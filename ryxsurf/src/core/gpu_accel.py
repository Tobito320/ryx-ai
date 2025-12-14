"""
GPU Acceleration

Hardware acceleration for rendering and compositing.
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("ryxsurf.gpu")


class GPUTier(Enum):
    """GPU performance tier"""
    DISABLED = 0
    SOFTWARE = 1
    BASIC = 2
    FULL = 3
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@dataclass
class GPUSettings:
    """GPU acceleration settings"""
    enabled: bool = True
    tier: GPUTier = GPUTier.FULL
    
    # Rendering
    hardware_acceleration: bool = True
    canvas_acceleration: bool = True
    webgl_enabled: bool = True
    webgl2_enabled: bool = True
    
    # Compositing
    accelerated_2d_canvas: bool = True
    accelerated_compositing: bool = True
    threaded_compositing: bool = True
    
    # Video
    hardware_video_decode: bool = True
    hardware_video_encode: bool = False
    
    # Advanced
    gpu_rasterization: bool = True
    zero_copy: bool = True
    native_gpu_memory_buffers: bool = True
    
    # Limits
    max_texture_size: int = 16384
    max_tiles: int = 128


class GPUAccelerator:
    """GPU acceleration manager"""
    
    def __init__(self):
        self.settings = GPUSettings()
        self.info: Dict = {}
        self._available = False
        self._tier = GPUTier.DISABLED
        
        self._detect_gpu()
        
        log.info(f"GPU acceleration initialized (tier: {self._tier.name})")
    
    def _detect_gpu(self):
        """Detect GPU capabilities"""
        # Try to detect GPU
        try:
            # Check for GPU via GI
            try:
                import gi
                gi.require_version('GdkPixbuf', '2.0')
                from gi.repository import Gdk
                
                display = Gdk.Display.get_default()
                if display:
                    self._available = True
                    
                    # Assume modern GPU
                    self._tier = GPUTier.FULL
                    
                    self.info = {
                        "available": True,
                        "vendor": "Unknown",
                        "renderer": "Unknown",
                        "version": "Unknown",
                        "tier": self._tier.name,
                    }
                    
                    log.info("GPU detected and available")
                    return
            except:
                pass
            
            # Fallback: check environment
            import os
            if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
                self._available = True
                self._tier = GPUTier.BASIC
                
                self.info = {
                    "available": True,
                    "vendor": "Unknown",
                    "renderer": "Software",
                    "version": "Unknown",
                    "tier": self._tier.name,
                }
                
                log.info("Display detected, using software rendering")
                return
        
        except Exception as e:
            log.warning(f"Failed to detect GPU: {e}")
        
        # No GPU
        self._available = False
        self._tier = GPUTier.DISABLED
        
        self.info = {
            "available": False,
            "tier": self._tier.name,
        }
        
        log.warning("No GPU detected")
    
    def get_webkit_settings(self) -> Dict:
        """Get WebKit settings for GPU acceleration"""
        if not self.settings.enabled or self._tier == GPUTier.DISABLED:
            return {
                "hardware-acceleration-policy": "never",
                "enable-webgl": False,
                "enable-accelerated-2d-canvas": False,
            }
        
        settings = {
            "hardware-acceleration-policy": "always" if self._tier >= GPUTier.FULL else "on-demand",
        }
        
        if self.settings.webgl_enabled:
            settings["enable-webgl"] = True
        
        if self.settings.accelerated_2d_canvas:
            settings["enable-accelerated-2d-canvas"] = True
        
        if self.settings.hardware_video_decode:
            settings["enable-media-stream"] = True
            settings["enable-media-capabilities"] = True
        
        return settings
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for GPU acceleration"""
        env = {}
        
        if not self.settings.enabled:
            return env
        
        # Force GPU acceleration
        if self._tier >= GPUTier.BASIC:
            env["WEBKIT_DISABLE_COMPOSITING_MODE"] = "0"
        
        if self._tier >= GPUTier.FULL:
            # Enable GPU rasterization
            env["WEBKIT_USE_GPU_RASTERIZATION"] = "1"
            
            # Enable zero copy
            if self.settings.zero_copy:
                env["WEBKIT_ENABLE_ZERO_COPY"] = "1"
        
        return env
    
    def set_tier(self, tier: GPUTier):
        """Set GPU acceleration tier"""
        if tier > self._tier and not self._available:
            log.warning(f"Cannot set tier to {tier.name}, GPU not available")
            return False
        
        self._tier = tier
        
        # Adjust settings based on tier
        if tier == GPUTier.DISABLED:
            self.settings.enabled = False
        elif tier == GPUTier.SOFTWARE:
            self.settings.hardware_acceleration = False
            self.settings.gpu_rasterization = False
        elif tier == GPUTier.BASIC:
            self.settings.hardware_acceleration = True
            self.settings.gpu_rasterization = False
            self.settings.threaded_compositing = False
        elif tier == GPUTier.FULL:
            self.settings.hardware_acceleration = True
            self.settings.gpu_rasterization = True
            self.settings.threaded_compositing = True
        
        log.info(f"GPU tier set to: {tier.name}")
        return True
    
    def get_info(self) -> Dict:
        """Get GPU information"""
        return {
            **self.info,
            "settings": {
                "enabled": self.settings.enabled,
                "tier": self._tier.name,
                "hardware_acceleration": self.settings.hardware_acceleration,
                "webgl": self.settings.webgl_enabled,
                "canvas_2d": self.settings.accelerated_2d_canvas,
                "video_decode": self.settings.hardware_video_decode,
                "gpu_rasterization": self.settings.gpu_rasterization,
            }
        }
    
    def enable(self):
        """Enable GPU acceleration"""
        if not self._available:
            log.warning("Cannot enable GPU acceleration, GPU not available")
            return False
        
        self.settings.enabled = True
        log.info("GPU acceleration enabled")
        return True
    
    def disable(self):
        """Disable GPU acceleration"""
        self.settings.enabled = False
        log.info("GPU acceleration disabled")
        return True
    
    def is_available(self) -> bool:
        """Check if GPU acceleration is available"""
        return self._available
    
    def get_recommended_settings(self) -> GPUSettings:
        """Get recommended settings based on detected GPU"""
        settings = GPUSettings()
        
        if self._tier == GPUTier.DISABLED:
            settings.enabled = False
            settings.tier = GPUTier.DISABLED
        elif self._tier == GPUTier.SOFTWARE:
            settings.tier = GPUTier.SOFTWARE
            settings.hardware_acceleration = False
        elif self._tier == GPUTier.BASIC:
            settings.tier = GPUTier.BASIC
            settings.gpu_rasterization = False
            settings.threaded_compositing = False
        else:  # FULL
            settings.tier = GPUTier.FULL
            # All features enabled (default)
        
        return settings


def create_gpu_accelerator() -> GPUAccelerator:
    """Create GPU accelerator"""
    return GPUAccelerator()
