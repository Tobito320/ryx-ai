"""
Dynamic Model Detection for Ryx AI

Automatically detects which model vLLM is serving and adapts.
No more hardcoded model paths that cause 404 errors.

Philosophy: Work with what's available, not what's expected.
"""

import requests
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Info about the currently loaded model"""
    name: str
    path: str
    created: int
    is_coding: bool = False
    is_fast: bool = False
    context_length: int = 8192
    
    def __post_init__(self):
        """Auto-detect model capabilities from name"""
        name_lower = self.name.lower()
        
        # Detect coding models
        self.is_coding = any(x in name_lower for x in ['coder', 'code', 'coding'])
        
        # Detect fast models (smaller parameter count)
        self.is_fast = any(x in name_lower for x in ['7b', '3b', '1.5b', '1b'])
        
        # Estimate context length from name
        if 'awq' in name_lower or '32k' in name_lower:
            self.context_length = 32768
        elif '16k' in name_lower:
            self.context_length = 16384
        elif 'gptq' in name_lower:
            self.context_length = 16384


class ModelDetector:
    """
    Detects and caches info about the vLLM model.
    
    Key features:
    - Auto-detects what model is loaded
    - Caches for 5 minutes (models don't change often)
    - Gracefully handles vLLM being down
    - Works with ANY model, no hardcoding
    """
    
    def __init__(self, vllm_url: str = "http://localhost:8001"):
        self.vllm_url = vllm_url
        self._cached_model: Optional[ModelInfo] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        
    def detect(self, force_refresh: bool = False) -> Optional[ModelInfo]:
        """
        Detect which model vLLM is serving.
        
        Args:
            force_refresh: Skip cache and query vLLM directly
            
        Returns:
            ModelInfo if vLLM is running, None otherwise
        """
        # Check cache
        if not force_refresh and self._cached_model and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_ttl:
                return self._cached_model
        
        # Query vLLM
        try:
            response = requests.get(
                f"{self.vllm_url}/v1/models",
                timeout=3
            )
            
            if response.status_code != 200:
                logger.warning(f"vLLM returned status {response.status_code}")
                return None
            
            data = response.json()
            models = data.get("data", [])
            
            if not models:
                logger.warning("vLLM returned no models")
                return None
            
            # Use first model (vLLM serves one model at a time)
            model_data = models[0]
            
            model_info = ModelInfo(
                name=model_data.get("id", "unknown"),
                path=model_data.get("id", "unknown"),
                created=model_data.get("created", 0)
            )
            
            # Cache it
            self._cached_model = model_info
            self._cache_time = datetime.now()
            
            logger.info(f"Detected model: {model_info.name}")
            return model_info
            
        except requests.exceptions.ConnectionError:
            logger.error("vLLM not running at {self.vllm_url}")
            return None
        except Exception as e:
            logger.error(f"Error detecting model: {e}")
            return None
    
    def get_model_for_task(self, task: str) -> Optional[str]:
        """
        Get the best model for a task.
        
        Since vLLM only serves one model, we always return that.
        But we log if it's not ideal for the task.
        
        Args:
            task: 'coding', 'chat', 'search', 'supervisor'
            
        Returns:
            Model name/path
        """
        model = self.detect()
        if not model:
            return None
        
        # Log warnings if model isn't ideal
        if task == 'coding' and not model.is_coding:
            logger.debug(f"Using {model.name} for coding (not a coding model)")
        elif task in ['supervisor', 'search'] and not model.is_fast:
            logger.debug(f"Using {model.name} for {task} (not optimized for speed)")
        
        return model.path
    
    def is_healthy(self) -> bool:
        """Check if vLLM is healthy"""
        try:
            response = requests.get(
                f"{self.vllm_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False


# Global singleton
_detector: Optional[ModelDetector] = None


def get_detector(vllm_url: str = None) -> ModelDetector:
    """Get or create the global model detector"""
    global _detector
    if _detector is None or vllm_url:
        import os
        url = vllm_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8001")
        _detector = ModelDetector(url)
    return _detector


def detect_model() -> Optional[ModelInfo]:
    """Convenience function to detect current model"""
    return get_detector().detect()
