"""
Ryx AI V2 - Model Orchestrator
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

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / "ryx-ai" / "configs" / "models.json"

        self.config_path = config_path
        self.ollama_url = "http://localhost:11434"

        # Model tiers
        self.model_tiers: Dict[str, ModelTier] = {}
        self.loaded_models: Dict[str, datetime] = {}  # model_name -> load_time
        self.model_performance: Dict[str, ModelPerformance] = {}

        # Configuration
        self.idle_timeout = timedelta(minutes=5)
        self.base_model_name = "qwen2.5:1.5b"  # Always loaded

        # Database for performance tracking
        self.db_path = Path.home() / "ryx-ai" / "data" / "model_performance.db"
        self._init_db()

        # Load configuration
        self._load_config()

        # Load base model immediately
        self._ensure_base_model_loaded()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

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

            # Parse model tiers
            for tier_name, tier_config in config.get("tiers", {}).items():
                self.model_tiers[tier_name] = ModelTier(**tier_config)

                # Initialize performance tracking
                model_name = tier_config["name"]
                if model_name not in self.model_performance:
                    self.model_performance[model_name] = ModelPerformance(
                        model_name=model_name
                    )
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
        - 0.0-0.5: Tier 1 (ultra-fast)
        - 0.5-0.7: Tier 2 (balanced)
        - 0.7-1.0: Tier 3 (powerful)
        """
        if complexity < 0.5:
            return self.model_tiers["ultra-fast"].name
        elif complexity < 0.7:
            return self.model_tiers["balanced"].name
        else:
            return self.model_tiers["powerful"].name

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

        # Preload by making a tiny request
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "test",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=30
            )

            if response.status_code == 200:
                self.loaded_models[model_name] = datetime.now()
                return True
            return False
        except:
            return False

    def _unload_model(self, model_name: str):
        """Unload a model (remove from loaded dict)"""
        if model_name in self.loaded_models and model_name != self.base_model_name:
            del self.loaded_models[model_name]

    def query(self,
              prompt: str,
              preferences: Optional[Dict] = None,
              system_context: str = "",
              model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Query with intelligent model selection

        Args:
            prompt: User query
            preferences: User preferences (from meta learner)
            system_context: Additional context
            model_override: Force specific model

        Returns:
            {
                "response": str,
                "model": str,
                "latency_ms": int,
                "complexity": float,
                "fallback_used": bool,
                "error": bool
            }
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

            return {
                "response": result["response"],
                "model": selected_model,
                "latency_ms": latency_ms,
                "complexity": complexity,
                "fallback_used": False,
                "error": False
            }

        # Primary failed, try fallback chain
        fallback_result = self._try_fallback_chain(
            selected_model, prompt, system_context, preferences
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if fallback_result["error"]:
            self._record_performance(selected_model, complexity, latency_ms, success=False)

        fallback_result["latency_ms"] = latency_ms
        fallback_result["complexity"] = complexity

        return fallback_result

    def _query_model(self,
                     model_name: str,
                     prompt: str,
                     system_context: str = "",
                     preferences: Optional[Dict] = None) -> Dict[str, Any]:
        """Query a specific model"""

        # Ensure model is loaded
        if not self._load_model(model_name):
            return {
                "response": f"Model {model_name} not available",
                "error": True
            }

        # Build system prompt
        system_prompt = self._build_system_prompt(system_context, preferences)

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\nUser: {prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2048
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "response": data.get("response", ""),
                    "error": False
                }
            else:
                return {
                    "response": f"Error: Status {response.status_code}",
                    "error": True
                }

        except requests.exceptions.ConnectionError:
            return {
                "response": "Error: Cannot connect to Ollama",
                "error": True
            }
        except Exception as e:
            return {
                "response": f"Error: {str(e)}",
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

    def _build_system_prompt(self, context: str = "", preferences: Optional[Dict] = None) -> str:
        """Build system prompt with preferences"""
        base = """You are Ryx, an ultra-efficient Arch Linux CLI assistant.

CRITICAL RULES:
1. Be EXTREMELY COMPACT - no fluff, no repetition
2. For file operations: give EXACT bash commands in ```bash blocks
3. For questions: answer in 1-2 sentences max
4. NEVER explain what you're doing - just do it
5. Use full paths always

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
