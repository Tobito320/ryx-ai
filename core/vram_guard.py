"""
Ryx AI - VRAM Guard & Model Manager

Manages GPU VRAM usage to prevent system instability:
- Monitors current VRAM usage
- Refuses to load models if > 90% VRAM would be used
- Suggests model offloading or switching
- Provides user feedback for model management

Based on user requirements:
- AMD RX 7800 XT (16GB VRAM)
- Max 90% VRAM usage (screen flickers above)
"""

import os
import re
import json
import subprocess
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# Default VRAM limits based on user's GPU
DEFAULT_VRAM_MB = 16384  # 16GB for RX 7800 XT
MAX_VRAM_PERCENT = 90.0  # User reports screen flickers above 90%


@dataclass
class VRAMStatus:
    """Current VRAM usage status"""
    total_mb: int = DEFAULT_VRAM_MB
    used_mb: int = 0
    free_mb: int = DEFAULT_VRAM_MB
    usage_percent: float = 0.0
    loaded_models: List[str] = field(default_factory=list)
    
    @property
    def is_safe(self) -> bool:
        """Check if VRAM usage is in safe range"""
        return self.usage_percent < MAX_VRAM_PERCENT
    
    @property
    def available_mb(self) -> int:
        """Calculate available VRAM (respecting 90% limit)"""
        max_usable = int(self.total_mb * (MAX_VRAM_PERCENT / 100))
        return max(0, max_usable - self.used_mb)


class LoadAction(Enum):
    """Action to take when loading a model"""
    LOAD = "load"           # Safe to load
    UNLOAD_FIRST = "unload_first"  # Need to unload other models first
    OFFLOAD_CPU = "offload_cpu"    # Offload to CPU memory
    REFUSE = "refuse"       # Cannot load without exceeding limits


@dataclass
class LoadDecision:
    """Decision about whether to load a model"""
    action: LoadAction
    model_name: str
    required_vram_mb: int
    available_vram_mb: int
    suggestion: str
    models_to_unload: List[str] = field(default_factory=list)


class VRAMGuard:
    """
    Monitors VRAM usage and prevents system instability.
    
    Features:
    - Real-time VRAM monitoring (AMD ROCm)
    - Model VRAM estimation
    - Load decision making
    - User feedback for model switching
    
    Usage:
        guard = VRAMGuard()
        
        # Check if safe to load
        decision = guard.can_load("qwen2.5-coder:14b")
        if decision.action == LoadAction.LOAD:
            # Safe to load
            pass
        elif decision.action == LoadAction.UNLOAD_FIRST:
            print(f"Unload first: {decision.models_to_unload}")
    """
    
    # Estimated VRAM requirements per model (MB)
    # Based on ~0.5-1GB per billion parameters for quantized models
    MODEL_VRAM_ESTIMATES: Dict[str, int] = {
        # Fast models
        "qwen2.5:1.5b": 1500,
        "qwen2.5:3b": 3000,
        
        # Medium models
        "qwen2.5:7b": 5000,
        "qwen2.5-coder:7b": 5000,
        "dolphin-mistral:7b": 5000,
        "gemma2:2b": 2000,
        
        # Large models
        "qwen2.5:14b": 10000,
        "qwen2.5-coder:14b": 10000,
        "mistral-nemo:12b": 8000,
        "deepseek-r1:14b": 10000,
        
        # Embedding models
        "nomic-embed-text:latest": 500,
        "nomic-embed-text": 500,
    }
    
    def __init__(self, max_vram_percent: float = MAX_VRAM_PERCENT):
        self.max_vram_percent = max_vram_percent
        self._cached_status: Optional[VRAMStatus] = None
    
    def get_vram_status(self, refresh: bool = False) -> VRAMStatus:
        """
        Get current VRAM usage status.
        
        Uses AMD ROCm tools (rocm-smi) for VRAM monitoring.
        Falls back to estimates if not available.
        """
        if self._cached_status is not None and not refresh:
            return self._cached_status
        
        status = VRAMStatus()
        
        # Try AMD ROCm tools
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram", "--json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Parse ROCm output (format varies by version)
                for card_id, info in data.items():
                    if isinstance(info, dict):
                        total = info.get("VRAM Total Memory (B)", 0)
                        used = info.get("VRAM Total Used Memory (B)", 0)
                        if total > 0:
                            status.total_mb = total // (1024 * 1024)
                            status.used_mb = used // (1024 * 1024)
                            status.free_mb = status.total_mb - status.used_mb
                            status.usage_percent = (status.used_mb / status.total_mb) * 100
                            break
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"ROCm tools not available: {e}")
            # Fall back to /sys/class/drm for AMD
            try:
                self._get_vram_from_sysfs(status)
            except Exception as e2:
                logger.debug(f"sysfs VRAM check failed: {e2}")
        
        # Get loaded models from Ollama
        status.loaded_models = self._get_loaded_models()
        
        self._cached_status = status
        return status
    
    def _get_vram_from_sysfs(self, status: VRAMStatus):
        """Try to get VRAM from sysfs (AMD GPUs)"""
        drm_path = "/sys/class/drm"
        if not os.path.exists(drm_path):
            return
        
        for card in os.listdir(drm_path):
            if not card.startswith("card"):
                continue
            
            mem_info = os.path.join(drm_path, card, "device", "mem_info_vram_total")
            mem_used = os.path.join(drm_path, card, "device", "mem_info_vram_used")
            
            if os.path.exists(mem_info) and os.path.exists(mem_used):
                with open(mem_info) as f:
                    status.total_mb = int(f.read().strip()) // (1024 * 1024)
                with open(mem_used) as f:
                    status.used_mb = int(f.read().strip()) // (1024 * 1024)
                status.free_mb = status.total_mb - status.used_mb
                status.usage_percent = (status.used_mb / status.total_mb) * 100
                break
    
    def _get_loaded_models(self) -> List[str]:
        """Get currently loaded models from Ollama"""
        try:
            import requests
            resp = requests.get(
                f"{os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}/api/ps",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Failed to get loaded models: {e}")
        return []
    
    def estimate_vram(self, model_name: str) -> int:
        """Estimate VRAM requirement for a model"""
        model_lower = model_name.lower()
        
        # Direct match
        if model_name in self.MODEL_VRAM_ESTIMATES:
            return self.MODEL_VRAM_ESTIMATES[model_name]
        
        # Check for parameter size indicators using regex (more precise)
        # Pattern matches: 14b, 7b, 1.5b, etc. at word boundaries
        param_match = re.search(r'[:\-_](\d+(?:\.\d+)?)(b)\b', model_lower)
        if param_match:
            param_size = float(param_match.group(1))
            if param_size >= 13:
                return 10000
            elif param_size >= 10:
                return 8000
            elif param_size >= 6:
                return 5000
            elif param_size >= 2.5:
                return 3000
            elif param_size >= 1:
                return 1500
            else:
                return 1000
        
        # Partial match (handle variations like qwen2.5:14b-instruct)
        for known_model, vram in self.MODEL_VRAM_ESTIMATES.items():
            if known_model.split(":")[0] in model_name:
                return vram
        
        # Default estimate for unknown models (assume medium size)
        return 5000
    
    def can_load(self, model_name: str) -> LoadDecision:
        """
        Determine if a model can be loaded safely.
        
        Returns LoadDecision with:
        - action: What to do (LOAD, UNLOAD_FIRST, OFFLOAD_CPU, REFUSE)
        - suggestion: Human-readable suggestion
        - models_to_unload: Which models to unload if needed
        """
        status = self.get_vram_status(refresh=True)
        required = self.estimate_vram(model_name)
        available = status.available_mb
        
        # Already loaded?
        if model_name in status.loaded_models:
            return LoadDecision(
                action=LoadAction.LOAD,
                model_name=model_name,
                required_vram_mb=required,
                available_vram_mb=available,
                suggestion=f"Model {model_name} is already loaded"
            )
        
        # Check if there's enough VRAM
        if required <= available:
            return LoadDecision(
                action=LoadAction.LOAD,
                model_name=model_name,
                required_vram_mb=required,
                available_vram_mb=available,
                suggestion=f"Safe to load {model_name} ({required}MB needed, {available}MB available)"
            )
        
        # Check if unloading other models would help
        potential_freed = sum(
            self.estimate_vram(m) for m in status.loaded_models
        )
        
        if required <= available + potential_freed:
            # Find models to unload (prefer smaller/less important)
            models_to_unload = self._select_models_to_unload(
                status.loaded_models,
                required - available
            )
            return LoadDecision(
                action=LoadAction.UNLOAD_FIRST,
                model_name=model_name,
                required_vram_mb=required,
                available_vram_mb=available,
                suggestion=f"Unload {', '.join(models_to_unload)} to free {required - available}MB",
                models_to_unload=models_to_unload
            )
        
        # Check if CPU offload is possible
        max_vram = int(status.total_mb * (self.max_vram_percent / 100))
        if required <= max_vram:
            return LoadDecision(
                action=LoadAction.OFFLOAD_CPU,
                model_name=model_name,
                required_vram_mb=required,
                available_vram_mb=available,
                suggestion=f"Consider CPU offload or unload all models first"
            )
        
        # Cannot load at all
        return LoadDecision(
            action=LoadAction.REFUSE,
            model_name=model_name,
            required_vram_mb=required,
            available_vram_mb=available,
            suggestion=f"Model {model_name} ({required}MB) exceeds safe VRAM limit ({max_vram}MB at {self.max_vram_percent}%)"
        )
    
    def _select_models_to_unload(
        self,
        loaded_models: List[str],
        needed_mb: int
    ) -> List[str]:
        """Select which models to unload to free up VRAM"""
        # Sort by VRAM usage (smaller first)
        models_by_vram = sorted(
            loaded_models,
            key=lambda m: self.estimate_vram(m)
        )
        
        to_unload = []
        freed = 0
        
        for model in models_by_vram:
            if freed >= needed_mb:
                break
            to_unload.append(model)
            freed += self.estimate_vram(model)
        
        return to_unload
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary"""
        status = self.get_vram_status(refresh=True)
        
        lines = [
            f"GPU VRAM: {status.used_mb}MB / {status.total_mb}MB ({status.usage_percent:.1f}%)",
        ]
        
        if status.loaded_models:
            lines.append(f"Loaded models: {', '.join(status.loaded_models)}")
        else:
            lines.append("No models loaded")
        
        if not status.is_safe:
            lines.append(f"⚠️ WARNING: VRAM usage above {MAX_VRAM_PERCENT}% - may cause instability")
        
        return "\n".join(lines)


class ModelManager:
    """
    High-level model management with VRAM awareness.
    
    Features:
    - Safe model loading with VRAM checks
    - Automatic unloading when needed
    - User prompts for confirmation
    - Status reporting for CLI/UI
    """
    
    def __init__(self, vram_guard: Optional[VRAMGuard] = None):
        self.vram_guard = vram_guard or VRAMGuard()
        self._ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    def load_model(
        self,
        model_name: str,
        auto_unload: bool = True,
        confirm_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """
        Load a model with VRAM safety checks.
        
        Args:
            model_name: Model to load
            auto_unload: Automatically unload other models if needed
            confirm_callback: Callback for user confirmation (returns bool)
        
        Returns:
            (success, message) tuple
        """
        decision = self.vram_guard.can_load(model_name)
        
        if decision.action == LoadAction.LOAD:
            # Safe to load directly
            return self._do_load(model_name)
        
        elif decision.action == LoadAction.UNLOAD_FIRST:
            if auto_unload:
                # Unload models automatically
                for model in decision.models_to_unload:
                    success, msg = self.unload_model(model)
                    if not success:
                        return False, f"Failed to unload {model}: {msg}"
                return self._do_load(model_name)
            elif confirm_callback:
                # Ask for confirmation
                if confirm_callback(decision.suggestion):
                    for model in decision.models_to_unload:
                        self.unload_model(model)
                    return self._do_load(model_name)
                return False, "User cancelled"
            else:
                return False, decision.suggestion
        
        elif decision.action == LoadAction.OFFLOAD_CPU:
            # TODO: Implement CPU offload via Ollama options
            return False, decision.suggestion
        
        else:  # REFUSE
            return False, decision.suggestion
    
    def _do_load(self, model_name: str) -> Tuple[bool, str]:
        """Actually load the model via Ollama"""
        try:
            import requests
            resp = requests.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",  # Empty prompt just to load
                    "options": {"num_predict": 1}
                },
                timeout=120  # Models can take time to load
            )
            if resp.status_code == 200:
                return True, f"Loaded {model_name}"
            return False, f"Failed to load: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Error loading model: {e}"
    
    def unload_model(self, model_name: str) -> Tuple[bool, str]:
        """Unload a model from Ollama"""
        try:
            import requests
            # Ollama doesn't have explicit unload, but we can try keepalive=0
            resp = requests.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "keep_alive": 0
                },
                timeout=30
            )
            if resp.status_code == 200:
                return True, f"Unloaded {model_name}"
            return False, f"Failed to unload: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Error unloading: {e}"
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded models with details"""
        try:
            import requests
            resp = requests.get(f"{self._ollama_url}/api/ps", timeout=5)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except Exception:
            pass
        return []
    
    def get_available_models(self) -> List[str]:
        """Get list of available (downloaded) models"""
        try:
            import requests
            resp = requests.get(f"{self._ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive model status"""
        vram_status = self.vram_guard.get_vram_status(refresh=True)
        
        return {
            "vram": {
                "total_mb": vram_status.total_mb,
                "used_mb": vram_status.used_mb,
                "free_mb": vram_status.free_mb,
                "usage_percent": vram_status.usage_percent,
                "is_safe": vram_status.is_safe,
            },
            "loaded_models": self.get_loaded_models(),
            "available_models": self.get_available_models(),
        }


# ═══════════════════════════════════════════════════════════════
# Singleton & Helper Functions
# ═══════════════════════════════════════════════════════════════

_vram_guard: Optional[VRAMGuard] = None
_model_manager: Optional[ModelManager] = None


def get_vram_guard() -> VRAMGuard:
    """Get or create the VRAM guard singleton"""
    global _vram_guard
    if _vram_guard is None:
        _vram_guard = VRAMGuard()
    return _vram_guard


def get_model_manager() -> ModelManager:
    """Get or create the model manager singleton"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
