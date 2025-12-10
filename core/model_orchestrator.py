"""
Ryx AI - Model Orchestrator
Intelligent model selection, lazy loading, and dynamic resource management
"""

import time
import json
import requests
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import sqlite3
import logging
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

logger = logging.getLogger(__name__)

@dataclass
class ModelTier:
    """Model specification for a tier"""
    name: str
    vram_mb: int
    typical_latency_ms: int
    specialties: List[str]
    tier_level: int  # 1=always loaded, 2=on-demand, 3=rare

@dataclass
class ModelPerformance:
    """Track model performance metrics"""
    model_name: str
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    last_used: Optional[datetime] = None
    complexity_scores: List[float] = field(default_factory=list)

@dataclass
class QueryResult:
    """Result from a model query"""
    response: str
    model_used: str
    tier_used: 'ModelTier'
    latency_ms: float
    complexity_score: float
    from_cache: bool = False
    error: Optional[str] = None

class ModelOrchestrator:
    """
    Orchestrates multiple AI models with intelligent loading and unloading

    Features:
    - Lazy Loading: Only loads base model (1.5B) on startup
    - Dynamic Loading: Loads larger models based on query complexity
    - Auto-Unload: Unloads idle models after 5 minutes
    - Fallback Chains: Automatically falls back to smaller models on failure
    - Performance Tracking: Learns which models work best for different tasks
    """

    # Default tier level mappings for config compatibility
    DEFAULT_TIER_LEVELS = {
        "fast": 1, "ultra-fast": 1,
        "balanced": 2,
        "powerful": 3,
        "ultra": 3,
        "uncensored": 2
    }

    def __init__(self, config_path: Optional[Path] = None, metrics_collector=None) -> None:
        """Initialize model orchestrator with lazy loading and performance tracking"""
        if config_path is None:
            config_path = get_project_root() / "configs" / "models.json"

        self.config_path = config_path
        self.ollama_url = "http://localhost:11434"  # Ollama API

        # Model tiers
        self.model_tiers: Dict[str, ModelTier] = {}
        self.loaded_models: Dict[str, datetime] = {}  # model_name -> load_time
        self.model_performance: Dict[str, ModelPerformance] = {}

        # Configuration
        self.idle_timeout = timedelta(minutes=5)
        
        # Base model for Ollama
        self.base_model_name = "qwen2.5:1.5b"  # Ultra-fast base model

        # Database for performance tracking
        self.db_path = get_project_root() / "data" / "model_performance.db"
        self._init_db()

        # Load configuration
        self._load_config()

        # Ollama auto-loads models on demand - no need to pre-load

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        # Metrics collector (optional integration)
        self.metrics_collector = metrics_collector

    def _init_db(self):
        """Initialize performance tracking database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                model_name TEXT PRIMARY KEY,
                total_queries INTEGER DEFAULT 0,
                successful_queries INTEGER DEFAULT 0,
                failed_queries INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0.0,
                total_latency_ms REAL DEFAULT 0.0,
                last_used TEXT,
                complexity_data TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _load_config(self):
        """Load model configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Parse model tiers - support both 'tiers' and 'models' keys
            tiers_data = config.get("tiers", config.get("models", {}))

            for tier_name, tier_config in tiers_data.items():
                # Handle different config formats
                # New format has full ModelTier fields
                # Old format (models.json) has different fields
                if "tier_level" not in tier_config:
                    # Map old format to new format using class constant
                    tier_config = {
                        "name": tier_config.get("name", "unknown"),
                        "vram_mb": tier_config.get("vram_mb", 4000),
                        "typical_latency_ms": tier_config.get("typical_latency_ms", 500),
                        "specialties": tier_config.get("specialties", []),
                        "tier_level": self.DEFAULT_TIER_LEVELS.get(tier_name, 2)
                    }

                self.model_tiers[tier_name] = ModelTier(**tier_config)

                # Initialize performance tracking
                model_name = tier_config["name"]
                if model_name not in self.model_performance:
                    self.model_performance[model_name] = ModelPerformance(
                        model_name=model_name
                    )

            # Ensure we have at least basic tiers for fallback
            if not self.model_tiers:
                self._create_default_config()
                self._load_config()

        except FileNotFoundError:
            # Use defaults if config doesn't exist
            self._create_default_config()
            self._load_config()

    def _create_default_config(self):
        """Create default model configuration"""
        default_config = {
            "tiers": {
                "ultra-fast": {
                    "name": "qwen2.5:1.5b",
                    "vram_mb": 1500,
                    "typical_latency_ms": 50,
                    "specialties": ["commands", "simple_queries", "file_operations"],
                    "tier_level": 1
                },
                "balanced": {
                    "name": "deepseek-coder:6.7b",
                    "vram_mb": 4000,
                    "typical_latency_ms": 500,
                    "specialties": ["code", "scripts", "moderate_complexity"],
                    "tier_level": 2
                },
                "powerful": {
                    "name": "qwen2.5-coder:14b",
                    "vram_mb": 9000,
                    "typical_latency_ms": 2000,
                    "specialties": ["architecture", "complex_reasoning", "refactoring"],
                    "tier_level": 3
                }
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

    def _ensure_base_model_loaded(self):
        """Ensure base model is loaded (lazy loading)"""
        if self.base_model_name not in self.loaded_models:
            if self._is_model_available(self.base_model_name):
                self.loaded_models[self.base_model_name] = datetime.now()

    def _is_model_available(self, model_name: str) -> bool:
        """Check if model is available in Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(m["name"] == model_name for m in models)
            return False
        except:
            return False

    def analyze_complexity(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Analyze query complexity (0.0 - 1.0)

        Factors:
        - Query length
        - Technical keywords
        - Code indicators
        - Architecture keywords
        - Context size

        Returns:
            0.0-0.5: Simple (use tier 1)
            0.5-0.7: Moderate (use tier 2)
            0.7-1.0: Complex (use tier 3)
        """
        score = 0.0
        query_lower = query.lower()
        words = query.split()

        # Length factor (0.0 - 0.2)
        if len(words) < 5:
            score += 0.0
        elif len(words) < 10:
            score += 0.1
        elif len(words) < 20:
            score += 0.15
        else:
            score += 0.2

        # Simple operation keywords (reduce complexity)
        simple_keywords = [
            "open", "find", "show", "list", "get", "where is",
            "how to", "what is", "search", "locate"
        ]
        if any(kw in query_lower for kw in simple_keywords):
            score -= 0.15

        # Code indicators (increase complexity)
        code_indicators = [
            "function", "class", "def", "import", "return",
            "if", "for", "while", "try", "except"
        ]
        code_count = sum(1 for kw in code_indicators if kw in query_lower)
        score += min(0.3, code_count * 0.1)

        # Architecture/complex keywords (increase complexity)
        complex_keywords = [
            "refactor", "architect", "design pattern", "optimize",
            "analyze", "compare", "evaluate", "implement system",
            "debug complex", "performance", "scalability"
        ]
        if any(kw in query_lower for kw in complex_keywords):
            score += 0.3

        # Medium complexity keywords
        medium_keywords = [
            "explain", "write code", "script", "automate",
            "configure", "setup", "install"
        ]
        if any(kw in query_lower for kw in medium_keywords):
            score += 0.2

        # Code block detection (increase complexity)
        if "```" in query or "def " in query or "class " in query:
            score += 0.25

        # Context size (0.0 - 0.15)
        if context:
            context_size = len(str(context))
            if context_size > 2000:
                score += 0.15
            elif context_size > 500:
                score += 0.1

        # Clamp to 0.0 - 1.0
        return max(0.0, min(1.0, score))

    def select_model(self, complexity: float) -> str:
        """
        Select appropriate model based on complexity score

        Complexity ranges:
        - 0.0-0.5: Tier 1 (fast/ultra-fast)
        - 0.5-0.7: Tier 2 (balanced)
        - 0.7-1.0: Tier 3 (powerful/ultra)
        
        Handles both 'ultra-fast' and 'fast' tier names for compatibility.
        """
        # Define tier priority for each complexity level
        if complexity < 0.5:
            # Try ultra-fast first, then fast as fallback
            tier_priority = ["ultra-fast", "fast"]
        elif complexity < 0.7:
            tier_priority = ["balanced"]
        else:
            # Try powerful first, then ultra as fallback
            tier_priority = ["powerful", "ultra"]
        
        # Find first available tier
        for tier_name in tier_priority:
            if tier_name in self.model_tiers:
                return self.model_tiers[tier_name].name
        
        # Ultimate fallback - return first available model
        if self.model_tiers:
            return next(iter(self.model_tiers.values())).name
        
        # If no tiers configured, return base model
        return self.base_model_name

    def _load_model(self, model_name: str) -> bool:
        """
        Load a model (if not already loaded)

        Returns True if successfully loaded or already loaded
        """
        if model_name in self.loaded_models:
            # Already loaded, just update timestamp
            self.loaded_models[model_name] = datetime.now()
            return True

        # Check if model is available
        if not self._is_model_available(model_name):
            return False

        # Ollama auto-loads models on first use - just mark as loaded
        self.loaded_models[model_name] = datetime.now()
        return True

    def _unload_model(self, model_name: str):
        """Unload a model (remove from loaded dict)"""
        if model_name in self.loaded_models and model_name != self.base_model_name:
            del self.loaded_models[model_name]

    def _get_tier_for_model(self, model_name: str) -> ModelTier:
        """Get the tier object for a given model name"""
        for tier_name, tier in self.model_tiers.items():
            if tier.name == model_name:
                return tier
        # Default to ultra-fast if not found
        return self.model_tiers.get("ultra-fast", ModelTier(
            name=model_name,
            vram_mb=1500,
            typical_latency_ms=50,
            specialties=["unknown"],
            tier_level=1
        ))

    def query(self,
              prompt: str,
              preferences: Optional[Dict] = None,
              system_context: str = "",
              model_override: Optional[str] = None) -> QueryResult:
        """
        Query with intelligent model selection

        Args:
            prompt: User query
            preferences: User preferences (from meta learner)
            system_context: Additional context
            model_override: Force specific model

        Returns:
            QueryResult object with response, model info, and performance metrics
        """
        start_time = time.time()

        # Analyze complexity
        context = {"system": system_context, "preferences": preferences}
        complexity = self.analyze_complexity(prompt, context)

        # Select model
        if model_override:
            selected_model = model_override
        else:
            selected_model = self.select_model(complexity)

        # Get the tier for the selected model
        tier = self._get_tier_for_model(selected_model)

        # Try primary model
        result = self._query_model(
            model_name=selected_model,
            prompt=prompt,
            system_context=system_context,
            preferences=preferences
        )

        if not result["error"]:
            # Success!
            latency_ms = int((time.time() - start_time) * 1000)
            self._record_performance(selected_model, complexity, latency_ms, success=True)

            # Record metrics if collector available
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_query(
                        query_type='model_query',
                        latency_ms=latency_ms,
                        success=True,
                        model_used=selected_model
                    )
                except Exception as e:
                    logger.warning(f"Failed to record metrics: {e}")

            return QueryResult(
                response=result["response"],
                model_used=selected_model,
                tier_used=tier,
                latency_ms=latency_ms,
                complexity_score=complexity,
                from_cache=False,
                error=None
            )

        # Primary failed, try fallback chain
        fallback_result = self._try_fallback_chain(
            selected_model, prompt, system_context, preferences
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if fallback_result["error"]:
            self._record_performance(selected_model, complexity, latency_ms, success=False)

            # Record failure metrics
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_query(
                        query_type='model_query',
                        latency_ms=latency_ms,
                        success=False,
                        model_used=selected_model
                    )
                except Exception as e:
                    logger.warning(f"Failed to record metrics: {e}")

            return QueryResult(
                response=fallback_result.get("response", "All models failed"),
                model_used=fallback_result.get("model", selected_model),
                tier_used=tier,
                latency_ms=latency_ms,
                complexity_score=complexity,
                from_cache=False,
                error=str(fallback_result.get("response", "Model query failed"))
            )

        # Fallback succeeded
        fallback_model = fallback_result.get("model", selected_model)
        fallback_tier = self._get_tier_for_model(fallback_model)

        return QueryResult(
            response=fallback_result["response"],
            model_used=fallback_model,
            tier_used=fallback_tier,
            latency_ms=latency_ms,
            complexity_score=complexity,
            from_cache=False,
            error=None
        )

    def _query_model(self,
                     model_name: str,
                     prompt: str,
                     system_context: str = "",
                     preferences: Optional[Dict] = None) -> Dict[str, Any]:
        """Query a specific model via Ollama API"""

        # Build system prompt with model identification
        system_prompt = self._build_system_prompt(system_context, preferences, model_name)

        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                # Ollama chat API format
                response = requests.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    # Ollama format: {"message": {"content": "..."}}
                    content = data.get("message", {}).get("content", "")
                    return {
                        "response": content,
                        "error": False
                    }
                elif response.status_code == 503 or response.status_code == 429:
                    # Service unavailable or too many requests
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Ollama busy, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        return {
                            "response": "⏱️ Ollama is busy. Please try again in a moment.",
                            "error": True
                        }
                else:
                    return {
                        "response": f"Error: Status {response.status_code} - {response.text[:100]}",
                        "error": True
                    }

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"Connection error, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "response": (
                            "❌ Cannot connect to Ollama service\n\n"
                            "Possible fixes:\n"
                            "  1. Start Ollama: ollama serve\n"
                            "  2. Check if Ollama is running: curl http://localhost:11434\n"
                            "  3. Wait if Ollama is busy with another request\n"
                        ),
                        "error": True
                    }
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"Request timeout, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "response": (
                            "⏱️  Ollama request timed out\n\n"
                            "Ollama may be busy with another request. Try again in a moment."
                        ),
                        "error": True
                    }
            except Exception as e:
                return {
                    "response": f"Error: {str(e)}",
                    "error": True
                }

        # Should not reach here, but just in case
        return {
            "response": "Unexpected error in retry logic",
            "error": True
        }

    def _try_fallback_chain(self,
                           failed_model: str,
                           prompt: str,
                           system_context: str,
                           preferences: Optional[Dict]) -> Dict[str, Any]:
        """
        Try fallback models in order of decreasing capability

        Fallback order:
        - powerful -> balanced -> ultra-fast
        - balanced -> ultra-fast
        - ultra-fast -> (no fallback)
        """
        # Define fallback chains
        fallback_chains = {
            "qwen2.5-coder:14b": ["deepseek-coder:6.7b", "qwen2.5:1.5b"],
            "deepseek-coder:6.7b": ["qwen2.5:1.5b"],
            "qwen2.5:1.5b": []
        }

        fallbacks = fallback_chains.get(failed_model, [])

        for fallback_model in fallbacks:
            result = self._query_model(
                model_name=fallback_model,
                prompt=prompt,
                system_context=system_context,
                preferences=preferences
            )

            if not result["error"]:
                return {
                    "response": result["response"],
                    "model": fallback_model,
                    "fallback_used": True,
                    "error": False,
                    "original_model": failed_model
                }

        return {
            "response": f"All models failed. Primary: {failed_model}",
            "model": None,
            "fallback_used": True,
            "error": True
        }

    def _build_system_prompt(self, context: str = "", preferences: Optional[Dict] = None, model_name: Optional[str] = None) -> str:
        """Build system prompt with preferences and model identification"""
        # Determine which model is being used
        current_model = model_name or self.base_model_name

        # Model-specific identity
        model_identity = f"You are Ryx, an ultra-efficient Arch Linux CLI assistant powered by {current_model}."

        base = model_identity + f"""

IDENTITY:
- You are running on the {current_model} model
- If asked "what model are you" or similar, respond: "I'm using {current_model}"
- If asked "which model" or "what model", always mention your current model: {current_model}

CRITICAL RULES:
1. DISTINGUISH conversation from commands:
   - If user is just talking/chatting → respond conversationally, NO commands
   - Only generate commands when user explicitly asks for action
   - NEVER hallucinate paths/files from conversational context

2. Command Detection:
   - "please open X" → generate command
   - "today I went to the store" → just conversation, NO command
   - "what's the time?" → generate command
   - "I like pizza" → just chat, NO command

3. Be EXTREMELY COMPACT - no fluff, no repetition
4. For file operations: give EXACT bash commands in ```bash blocks ONLY when requested
5. For questions: answer in 1-2 sentences max
6. NEVER explain what you're doing - just do it
7. Use full paths always for actual files/directories only
8. PRESERVE exact spelling from user queries (e.g., "hyprland" not "hyrangee")
9. Double-check command names and paths before suggesting them
10. For "separate terminals" or "new terminals": use "kitty -e nvim file &" for EACH file
11. When opening MULTIPLE files in separate terminals: generate separate "kitty -e nvim file &" for each
12. Extract EXACT filenames from user input - don't hallucinate or guess names
13. If user lists files with bullets/dashes, extract ONLY the filenames, ignore formatting

EXAMPLES:

Conversation vs Command:
User: "today I went to the supermarket"
Response: Cool! How was the trip?
(NO bash commands - just conversation)

User: "today I went to the supermarket so please open a new terminal"
Response: ```bash
kitty &
```
(ONLY command for "open new terminal", ignore "supermarket" context)

Commands:
User: "open file1.txt and file2.txt in separate terminals"
Response: ```bash
kitty -e nvim file1.txt &
kitty -e nvim file2.txt &
```

User: "open these 3 files in new terminals: - config.yml - setup.sh - README.md"
Response: ```bash
kitty -e nvim config.yml &
kitty -e nvim setup.sh &
kitty -e nvim README.md &
```

"""

        if preferences:
            base += "USER PREFERENCES:\n"
            if "editor" in preferences:
                base += f"- Editor: {preferences['editor']}\n"
            if "shell" in preferences:
                base += f"- Shell: {preferences['shell']}\n"
            if "theme" in preferences:
                base += f"- Theme: {preferences['theme']}\n"

        if context:
            base += f"\nCONTEXT:\n{context}\n"

        return base

    def _record_performance(self, model_name: str, complexity: float, latency_ms: int, success: bool):
        """Record model performance metrics"""
        if model_name not in self.model_performance:
            self.model_performance[model_name] = ModelPerformance(model_name=model_name)

        perf = self.model_performance[model_name]
        perf.total_queries += 1

        if success:
            perf.successful_queries += 1
            perf.total_latency_ms += latency_ms
            perf.avg_latency_ms = perf.total_latency_ms / perf.successful_queries
        else:
            perf.failed_queries += 1

        perf.complexity_scores.append(complexity)
        perf.last_used = datetime.now()

        # Save to database
        self._save_performance(perf)

    def _save_performance(self, perf: ModelPerformance):
        """Save performance data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO model_performance
            (model_name, total_queries, successful_queries, failed_queries,
             avg_latency_ms, total_latency_ms, last_used, complexity_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            perf.model_name,
            perf.total_queries,
            perf.successful_queries,
            perf.failed_queries,
            perf.avg_latency_ms,
            perf.total_latency_ms,
            perf.last_used.isoformat() if perf.last_used else None,
            json.dumps(perf.complexity_scores[-100:])  # Keep last 100
        ))

        conn.commit()
        conn.close()

    def _cleanup_loop(self):
        """Background thread to unload idle models"""
        while True:
            time.sleep(60)  # Check every minute
            self._cleanup_idle_models()

    def _cleanup_idle_models(self):
        """Unload models that have been idle for > 5 minutes"""
        now = datetime.now()
        to_unload = []

        for model_name, load_time in self.loaded_models.items():
            if model_name == self.base_model_name:
                continue  # Never unload base model

            if now - load_time > self.idle_timeout:
                to_unload.append(model_name)

        for model_name in to_unload:
            self._unload_model(model_name)

    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a specific model

        Args:
            model_name: Model to switch to

        Returns:
            True if successful
        """
        if not self._is_model_available(model_name):
            raise ValueError(f"Model {model_name} is not available")

        # Update base model
        self.base_model_name = model_name

        # Ensure it's loaded
        if model_name not in self.loaded_models:
            success = self._load_model(model_name)
            if not success:
                raise RuntimeError(f"Failed to load model {model_name}")

        return True

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "loaded_models": list(self.loaded_models.keys()),
            "base_model": self.base_model_name,
            "performance": {
                name: {
                    "total_queries": perf.total_queries,
                    "success_rate": perf.successful_queries / perf.total_queries if perf.total_queries > 0 else 0,
                    "avg_latency_ms": perf.avg_latency_ms
                }
                for name, perf in self.model_performance.items()
            }
        }
