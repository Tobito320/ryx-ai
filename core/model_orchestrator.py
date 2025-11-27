"""
Ryx AI - Model Orchestrator with Lazy Loading
Intelligently routes queries to optimal models, loading larger models only when needed
"""

import json
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model performance tiers"""
    ULTRA_FAST = 1  # 1.5B - always loaded
    BALANCED = 2    # 7B - load on demand
    POWERFUL = 3    # 14B+ - load rarely


@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    tier: ModelTier
    vram_mb: int
    typical_latency_ms: int
    specialties: List[str]
    quantization: Optional[str] = None


@dataclass
class QueryResult:
    """Result from model query"""
    response: str
    model_used: str
    latency_ms: int
    complexity_score: float
    tier_used: ModelTier
    was_loaded: bool  # Was model already loaded or did we load it?


class ComplexityAnalyzer:
    """Analyzes query complexity to determine optimal model tier"""
    
    def __init__(self):
        self.history: List[Tuple[str, float, ModelTier, bool]] = []  # query, score, tier, success
    
    def analyze(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Analyze query complexity and return score 0.0-1.0
        
        Factors:
        - Token count
        - Code presence
        - Multi-step reasoning keywords
        - System vs creation task
        - Historical success rates
        """
        score = 0.0
        
        # Base complexity from length
        token_count = len(query.split())
        if token_count < 10:
            score += 0.1
        elif token_count < 30:
            score += 0.3
        elif token_count < 100:
            score += 0.5
        else:
            score += 0.7
        
        # Code-related queries
        code_keywords = ['function', 'class', 'script', 'code', 'program', 'algorithm', 'implement']
        if any(kw in query.lower() for kw in code_keywords):
            score += 0.2
        
        # Architecture/design queries
        design_keywords = ['architect', 'design', 'system', 'structure', 'organize', 'refactor']
        if any(kw in query.lower() for kw in design_keywords):
            score += 0.3
        
        # Simple commands (reduce score)
        simple_keywords = ['open', 'show', 'list', 'find', 'where', 'what is']
        if any(query.lower().startswith(kw) for kw in simple_keywords):
            score -= 0.3
        
        # Multi-step reasoning
        multi_step_keywords = ['analyze', 'compare', 'evaluate', 'optimize', 'review']
        if any(kw in query.lower() for kw in multi_step_keywords):
            score += 0.2
        
        # Clamp to 0.0-1.0
        score = max(0.0, min(1.0, score))
        
        # Adjust based on historical success
        score = self._adjust_for_history(query, score)
        
        return score
    
    def _adjust_for_history(self, query: str, base_score: float) -> float:
        """Adjust score based on similar past queries"""
        if not self.history:
            return base_score
        
        # Simple keyword-based similarity for now
        query_words = set(query.lower().split())
        
        similar_successes = []
        for past_query, past_score, tier, success in self.history[-100:]:
            past_words = set(past_query.lower().split())
            overlap = len(query_words & past_words) / len(query_words | past_words) if query_words | past_words else 0
            
            if overlap > 0.3:  # 30% word overlap
                similar_successes.append((tier, success))
        
        if similar_successes:
            # If similar queries succeeded with lower tier, reduce score
            lower_tier_successes = [s for t, s in similar_successes if t == ModelTier.ULTRA_FAST and s]
            if len(lower_tier_successes) > len(similar_successes) * 0.7:
                return base_score * 0.8
        
        return base_score
    
    def record_result(self, query: str, score: float, tier: ModelTier, success: bool):
        """Record query result for learning"""
        self.history.append((query, score, tier, success))
        if len(self.history) > 1000:
            self.history = self.history[-1000:]


class ModelOrchestrator:
    """
    Orchestrates model loading and query routing with lazy loading strategy.
    Only keeps smallest model loaded, dynamically loads bigger models as needed.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / "ryx-ai" / "configs" / "models.json"
        self.models: Dict[ModelTier, ModelConfig] = {}
        self.loaded_models: Dict[ModelTier, float] = {}  # tier -> timestamp of last use
        self.complexity_analyzer = ComplexityAnalyzer()
        self.ollama_url = "http://localhost:11434"
        
        # Unload timer
        self._unload_timer: Optional[threading.Timer] = None
        self._unload_interval = 300  # 5 minutes
        
        self._load_config()
        self._ensure_base_model_loaded()
    
    def _load_config(self):
        """Load model configurations"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Valid tier names that should be loaded
            valid_tiers = ['ultra-fast', 'balanced', 'powerful']

            for tier_name, model_data in config.items():
                # Skip non-model configuration keys
                if tier_name not in valid_tiers:
                    continue

                if not isinstance(model_data, dict) or 'name' not in model_data:
                    continue

                tier = ModelTier[tier_name.upper().replace('-', '_')]
                self.models[tier] = ModelConfig(
                    name=model_data['name'],
                    tier=tier,
                    vram_mb=model_data['vram_mb'],
                    typical_latency_ms=model_data['typical_latency_ms'],
                    specialties=model_data.get('specialties', []),
                    quantization=model_data.get('quantization')
                )
        else:
            # Default configuration
            self.models = {
                ModelTier.ULTRA_FAST: ModelConfig(
                    name="qwen2.5:1.5b",
                    tier=ModelTier.ULTRA_FAST,
                    vram_mb=1500,
                    typical_latency_ms=50,
                    specialties=["commands", "simple_queries", "file_operations"]
                ),
                ModelTier.BALANCED: ModelConfig(
                    name="deepseek-coder:6.7b",
                    tier=ModelTier.BALANCED,
                    vram_mb=4000,
                    typical_latency_ms=500,
                    specialties=["code", "scripts", "moderate_complexity"]
                ),
                ModelTier.POWERFUL: ModelConfig(
                    name="qwen2.5-coder:14b",
                    tier=ModelTier.POWERFUL,
                    vram_mb=9000,
                    typical_latency_ms=2000,
                    specialties=["architecture", "complex_reasoning", "refactoring"]
                )
            }
            self._save_config()
    
    def _save_config(self):
        """Save current model configuration"""
        config = {}
        for tier, model in self.models.items():
            config[tier.name.lower().replace('_', '-')] = {
                'name': model.name,
                'vram_mb': model.vram_mb,
                'typical_latency_ms': model.typical_latency_ms,
                'specialties': model.specialties,
                'quantization': model.quantization
            }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _ensure_base_model_loaded(self):
        """Ensure the ultra-fast model is always loaded"""
        if ModelTier.ULTRA_FAST not in self.loaded_models:
            self._load_model(ModelTier.ULTRA_FAST)
    
    def _is_model_loaded(self, model_name: str) -> bool:
        """Check if model is currently loaded in Ollama"""
        try:
            result = subprocess.run(
                ['ollama', 'ps'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return model_name in result.stdout
        except Exception as e:
            logger.warning(f"Failed to check model status: {e}")
            return False
    
    def _load_model(self, tier: ModelTier) -> bool:
        """Load a model into memory"""
        if tier not in self.models:
            logger.error(f"No model configured for tier {tier}")
            return False
        
        model = self.models[tier]
        
        # Check if already loaded
        if self._is_model_loaded(model.name):
            self.loaded_models[tier] = time.time()
            logger.info(f"Model {model.name} already loaded")
            return True
        
        logger.info(f"Loading model {model.name} for tier {tier.name}...")
        
        try:
            # Pull model if not available
            result = subprocess.run(
                ['ollama', 'pull', model.name],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.loaded_models[tier] = time.time()
                logger.info(f"Successfully loaded {model.name}")
                
                # Start unload timer for non-base models
                if tier != ModelTier.ULTRA_FAST:
                    self._schedule_unload()
                
                return True
            else:
                logger.error(f"Failed to load {model.name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading {model.name}: {e}")
            return False
    
    def _unload_model(self, tier: ModelTier):
        """Unload a model from memory"""
        if tier == ModelTier.ULTRA_FAST:
            return  # Never unload base model
        
        if tier not in self.loaded_models:
            return
        
        model = self.models[tier]
        
        # Check if recently used
        last_use = self.loaded_models[tier]
        if time.time() - last_use < self._unload_interval:
            return  # Still in use window
        
        try:
            # Stop the model
            subprocess.run(
                ['ollama', 'stop', model.name],
                capture_output=True,
                timeout=10
            )
            del self.loaded_models[tier]
            logger.info(f"Unloaded idle model {model.name}")
        except Exception as e:
            logger.warning(f"Failed to unload {model.name}: {e}")
    
    def _schedule_unload(self):
        """Schedule periodic check for idle models"""
        if self._unload_timer:
            self._unload_timer.cancel()
        
        self._unload_timer = threading.Timer(60, self._check_idle_models)
        self._unload_timer.daemon = True
        self._unload_timer.start()
    
    def _check_idle_models(self):
        """Check and unload idle models"""
        for tier in list(self.loaded_models.keys()):
            if tier != ModelTier.ULTRA_FAST:
                self._unload_model(tier)
        
        # Reschedule
        if any(t != ModelTier.ULTRA_FAST for t in self.loaded_models.keys()):
            self._schedule_unload()
    
    def query(self, prompt: str, context: Optional[Dict] = None) -> QueryResult:
        """
        Execute query with optimal model selection and lazy loading
        """
        start_time = time.time()
        
        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(prompt, context)
        
        # Determine tier
        if complexity < 0.5:
            tier = ModelTier.ULTRA_FAST
        elif complexity < 0.7:
            tier = ModelTier.BALANCED
        else:
            tier = ModelTier.POWERFUL
        
        logger.info(f"Query complexity: {complexity:.2f} -> Tier: {tier.name}")
        
        # Check if model is loaded
        was_loaded = tier in self.loaded_models
        
        # Load model if needed
        if not was_loaded:
            if not self._load_model(tier):
                # Fallback to lower tier
                logger.warning(f"Failed to load {tier.name}, falling back...")
                if tier == ModelTier.POWERFUL:
                    tier = ModelTier.BALANCED
                    was_loaded = tier in self.loaded_models
                    if not was_loaded and not self._load_model(tier):
                        tier = ModelTier.ULTRA_FAST
                        was_loaded = True
                elif tier == ModelTier.BALANCED:
                    tier = ModelTier.ULTRA_FAST
                    was_loaded = True
        
        # Execute query
        model = self.models[tier]
        
        try:
            import requests
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model.name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result_text = response.json().get('response', '')
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Update last use time
                self.loaded_models[tier] = time.time()
                
                # Record success
                self.complexity_analyzer.record_result(prompt, complexity, tier, True)
                
                return QueryResult(
                    response=result_text,
                    model_used=model.name,
                    latency_ms=latency_ms,
                    complexity_score=complexity,
                    tier_used=tier,
                    was_loaded=was_loaded
                )
            else:
                raise Exception(f"Ollama returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Query failed: {e}")
            self.complexity_analyzer.record_result(prompt, complexity, tier, False)
            
            # Try fallback tier
            if tier != ModelTier.ULTRA_FAST:
                logger.info("Attempting fallback to ultra-fast model...")
                fallback_model = self.models[ModelTier.ULTRA_FAST]
                try:
                    response = requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": fallback_model.name,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result_text = response.json().get('response', '')
                        latency_ms = int((time.time() - start_time) * 1000)
                        
                        return QueryResult(
                            response=result_text,
                            model_used=fallback_model.name,
                            latency_ms=latency_ms,
                            complexity_score=complexity,
                            tier_used=ModelTier.ULTRA_FAST,
                            was_loaded=True
                        )
                except:
                    pass
            
            # Complete failure
            raise Exception(f"All models failed for query")
    
    def get_status(self) -> Dict:
        """Get current orchestrator status"""
        return {
            'loaded_models': [
                {
                    'tier': tier.name,
                    'model': self.models[tier].name,
                    'last_used': time.time() - ts,
                    'vram_mb': self.models[tier].vram_mb
                }
                for tier, ts in self.loaded_models.items()
            ],
            'available_models': [
                {
                    'tier': tier.name,
                    'model': model.name,
                    'vram_mb': model.vram_mb,
                    'loaded': tier in self.loaded_models
                }
                for tier, model in self.models.items()
            ],
            'query_history': len(self.complexity_analyzer.history)
        }
