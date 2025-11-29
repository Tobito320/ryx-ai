"""
Ryx AI - Model Router
Intelligent model selection based on tiers and intent
"""

import json
import os
import requests
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.paths import get_project_root, get_config_dir


class ModelTier(Enum):
    """Model tier levels"""
    FAST = "fast"
    BALANCED = "balanced"
    POWERFUL = "powerful"
    ULTRA = "ultra"
    UNCENSORED = "uncensored"


@dataclass
class ModelConfig:
    """Configuration for a model tier"""
    model: str
    fallbacks: List[str]
    description: str
    max_tokens: int
    timeout_seconds: int
    use_cases: List[str]


@dataclass
class ModelResponse:
    """Response from model query"""
    response: str
    model_used: str
    tier_used: str
    latency_ms: int
    from_cache: bool = False
    error: bool = False
    error_message: Optional[str] = None
    tokens_used: int = 0


class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client"""
        self.base_url = os.environ.get('OLLAMA_BASE_URL', base_url)
        self.timeout = 120
    
    def list_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except Exception:
            pass
        return []
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available"""
        available = self.list_models()
        return model_name in available
    
    def generate(self, model: str, prompt: str, system: str = "", 
                stream: bool = False, options: Dict = None) -> Dict[str, Any]:
        """Generate response from model"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {"temperature": 0.3, "num_predict": 2048}
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": True, "message": f"Status {response.status_code}"}
        except requests.exceptions.Timeout:
            return {"error": True, "message": "Request timed out"}
        except requests.exceptions.ConnectionError:
            return {"error": True, "message": "Cannot connect to Ollama"}
        except Exception as e:
            return {"error": True, "message": str(e)}
    
    def generate_stream(self, model: str, prompt: str, system: str = "",
                       options: Dict = None) -> Generator[str, None, None]:
        """Generate streaming response from model"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": options or {"temperature": 0.3, "num_predict": 2048}
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"\n[Error: {str(e)}]"


class ModelRouter:
    """
    Routes queries to appropriate models based on intent and complexity
    
    Features:
    - Tier-based model selection
    - Automatic fallback chain
    - Streaming support
    - Docker-aware Ollama URL
    - User tier overrides
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize model router with configuration"""
        if config_path is None:
            config_path = get_config_dir() / "model_tiers.json"
        
        self.config_path = config_path
        self.config = self._load_config()
        self.ollama = OllamaClient(self.config.get('ollama_base_url', 'http://localhost:11434'))
        self.tiers: Dict[str, ModelConfig] = {}
        self.current_tier: str = self.config.get('default_tier', 'balanced')
        self.user_override: Optional[str] = None
        
        self._parse_tier_configs()
    
    def _load_config(self) -> Dict:
        """Load model tier configuration"""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """Create default configuration if none exists"""
        default = {
            "ollama_base_url": "http://localhost:11434",
            "tiers": {
                "fast": {
                    "model": "mistral:7b",
                    "fallbacks": [],
                    "description": "Fast responses",
                    "max_tokens": 1024,
                    "timeout_seconds": 20,
                    "use_cases": ["chat", "simple"]
                },
                "balanced": {
                    "model": "qwen2.5-coder:14b",
                    "fallbacks": ["mistral:7b"],
                    "description": "Default coding",
                    "max_tokens": 4096,
                    "timeout_seconds": 60,
                    "use_cases": ["code", "config"]
                }
            },
            "default_tier": "balanced"
        }
        return default
    
    def _parse_tier_configs(self):
        """Parse tier configurations from config"""
        for tier_name, tier_config in self.config.get('tiers', {}).items():
            self.tiers[tier_name] = ModelConfig(
                model=tier_config['model'],
                fallbacks=tier_config.get('fallbacks', []),
                description=tier_config.get('description', ''),
                max_tokens=tier_config.get('max_tokens', 2048),
                timeout_seconds=tier_config.get('timeout_seconds', 60),
                use_cases=tier_config.get('use_cases', [])
            )
    
    def set_tier(self, tier: str) -> bool:
        """Set the current tier for subsequent queries"""
        if tier in self.tiers:
            self.current_tier = tier
            self.user_override = tier
            return True
        return False
    
    def clear_override(self):
        """Clear user tier override"""
        self.user_override = None
        self.current_tier = self.config.get('default_tier', 'balanced')
    
    def get_tier_for_intent(self, intent_type: str) -> str:
        """Get appropriate tier for intent type"""
        if self.user_override:
            return self.user_override
        
        mapping = self.config.get('intent_to_tier_mapping', {})
        return mapping.get(intent_type, self.config.get('default_tier', 'balanced'))
    
    def select_model(self, tier: str) -> str:
        """Select best available model for tier"""
        if tier not in self.tiers:
            tier = self.config.get('default_tier', 'balanced')
        
        tier_config = self.tiers[tier]
        
        # Try primary model first
        if self.ollama.is_model_available(tier_config.model):
            return tier_config.model
        
        # Try fallbacks
        for fallback in tier_config.fallbacks:
            if self.ollama.is_model_available(fallback):
                return fallback
        
        # Ultimate fallback - try any available model
        available = self.ollama.list_models()
        if available:
            return available[0]
        
        raise RuntimeError("No models available in Ollama")
    
    def query(self, prompt: str, tier: Optional[str] = None, 
             system_context: str = "", stream: bool = False) -> ModelResponse:
        """
        Query the appropriate model
        
        Args:
            prompt: User prompt
            tier: Optional tier override
            system_context: System context/instructions
            stream: Whether to stream response
            
        Returns:
            ModelResponse with response and metadata
        """
        start_time = time.perf_counter()
        
        # Determine tier
        use_tier = tier or self.user_override or self.current_tier
        
        try:
            model = self.select_model(use_tier)
        except RuntimeError as e:
            return ModelResponse(
                response=str(e),
                model_used="none",
                tier_used=use_tier,
                latency_ms=0,
                error=True,
                error_message=str(e)
            )
        
        tier_config = self.tiers.get(use_tier)
        
        # Build system prompt
        system = self._build_system_prompt(model, system_context)
        
        options = {
            "temperature": 0.3,
            "num_predict": tier_config.max_tokens if tier_config else 2048
        }
        
        if stream:
            # For streaming, we collect the full response
            response_text = ""
            for chunk in self.ollama.generate_stream(model, prompt, system, options):
                response_text += chunk
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ModelResponse(
                response=response_text,
                model_used=model,
                tier_used=use_tier,
                latency_ms=latency_ms
            )
        else:
            result = self.ollama.generate(model, prompt, system, False, options)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            if result.get('error'):
                return ModelResponse(
                    response=result.get('message', 'Unknown error'),
                    model_used=model,
                    tier_used=use_tier,
                    latency_ms=latency_ms,
                    error=True,
                    error_message=result.get('message')
                )
            
            return ModelResponse(
                response=result.get('response', ''),
                model_used=model,
                tier_used=use_tier,
                latency_ms=latency_ms,
                tokens_used=result.get('eval_count', 0)
            )
    
    def _build_system_prompt(self, model: str, context: str = "") -> str:
        """Build system prompt with model identity"""
        return f"""You are Ryx, a local AI assistant running on {model}.

RULES:
1. Be concise - no fluff
2. For commands, use ```bash code blocks
3. Use full paths when referencing files
4. If asked about your model, say: "I'm using {model}"

{context}"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status"""
        available_models = self.ollama.list_models()
        
        tier_status = {}
        for tier_name, tier_config in self.tiers.items():
            primary_available = tier_config.model in available_models
            fallbacks_available = [f for f in tier_config.fallbacks if f in available_models]
            
            tier_status[tier_name] = {
                "model": tier_config.model,
                "available": primary_available,
                "fallbacks_available": fallbacks_available,
                "description": tier_config.description
            }
        
        return {
            "current_tier": self.current_tier,
            "user_override": self.user_override,
            "available_models": available_models,
            "tiers": tier_status,
            "ollama_url": self.ollama.base_url
        }
    
    def get_tier_info(self, tier: str) -> Optional[Dict]:
        """Get info about a specific tier"""
        if tier not in self.tiers:
            return None
        
        config = self.tiers[tier]
        return {
            "model": config.model,
            "description": config.description,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout_seconds,
            "use_cases": config.use_cases
        }
