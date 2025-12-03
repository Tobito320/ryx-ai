# -*- coding: utf-8 -*-
"""
Hardware Manager - Zentrale Verwaltung aller Hardware-Komponenten
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable, Any
import logging

from .camera import Camera, CameraConfig, Frame
from .face_detection import FaceDetector, FaceDetectorConfig, FaceResult

logger = logging.getLogger(__name__)


@dataclass
class HardwareConfig:
    """Gesamtkonfiguration für Hardware"""
    # Camera
    enable_camera: bool = False
    camera_device: int = 0
    camera_resolution: tuple = (640, 480)
    
    # Face Detection
    enable_face_detection: bool = False
    enable_face_recognition: bool = False
    
    # Sensors (für Zukunft)
    enable_sensors: bool = False
    
    # Presence Detection
    enable_presence: bool = False
    presence_timeout: float = 5.0  # Sekunden ohne Gesicht = nicht präsent


class HardwareManager:
    """
    Zentrale Verwaltung aller Ryx Hardware-Komponenten
    
    Features:
    - Kamera-Management
    - Face Detection & Recognition
    - Präsenz-Erkennung
    - Sensor-Integration (erweiterbar)
    
    Usage:
        hw = HardwareManager(HardwareConfig(
            enable_camera=True,
            enable_face_detection=True
        ))
        await hw.initialize()
        
        # Check user presence
        if await hw.is_user_present():
            print("User is here!")
            
        # Get camera frame
        frame = await hw.capture_frame()
        
        # Detect faces
        faces = await hw.detect_faces()
    """
    
    def __init__(self, config: Optional[HardwareConfig] = None):
        self.config = config or HardwareConfig()
        
        # Components
        self._camera: Optional[Camera] = None
        self._face_detector: Optional[FaceDetector] = None
        
        # State
        self._initialized = False
        self._last_face_time: float = 0
        self._user_present = False
        
        # Callbacks
        self._presence_callbacks: list = []
        
    async def initialize(self) -> bool:
        """Initialisiere alle aktivierten Hardware-Komponenten"""
        if self._initialized:
            return True
            
        success = True
        
        # Camera
        if self.config.enable_camera:
            self._camera = Camera(CameraConfig(
                device_id=self.config.camera_device,
                width=self.config.camera_resolution[0],
                height=self.config.camera_resolution[1]
            ))
            if not await self._camera.start():
                logger.warning("Camera initialization failed")
                success = False
                
        # Face Detection
        if self.config.enable_face_detection:
            self._face_detector = FaceDetector(FaceDetectorConfig(
                enable_recognition=self.config.enable_face_recognition
            ))
            if not await self._face_detector.initialize():
                logger.warning("Face detector initialization failed")
                success = False
                
        # Presence monitoring
        if self.config.enable_presence and self._camera and self._face_detector:
            asyncio.create_task(self._presence_monitor_loop())
            
        self._initialized = success
        logger.info(f"Hardware manager initialized (success={success})")
        return success
        
    async def shutdown(self):
        """Beende alle Hardware-Komponenten"""
        if self._camera:
            await self._camera.stop()
            
        self._initialized = False
        logger.info("Hardware manager shutdown")
        
    async def capture_frame(self) -> Optional[Frame]:
        """Einzelnes Frame von der Kamera aufnehmen"""
        if not self._camera:
            logger.warning("Camera not initialized")
            return None
            
        return await self._camera.capture_single()
        
    async def detect_faces(self, frame: Optional[Frame] = None) -> FaceResult:
        """Gesichtserkennung durchführen"""
        if not self._face_detector:
            return FaceResult()
            
        if frame is None:
            frame = await self.capture_frame()
            
        if frame is None:
            return FaceResult()
            
        return await self._face_detector.detect(frame)
        
    async def is_user_present(self) -> bool:
        """Prüfe ob Benutzer präsent ist (basierend auf Gesichtserkennung)"""
        if not self.config.enable_presence:
            return True  # Assume present wenn Presence nicht aktiviert
            
        return self._user_present
        
    def on_presence_change(self, callback: Callable[[bool], None]):
        """Registriere Callback für Präsenz-Änderungen"""
        self._presence_callbacks.append(callback)
        
    async def _presence_monitor_loop(self):
        """Hintergrund-Loop für Präsenz-Überwachung"""
        import time
        
        while self._initialized:
            try:
                result = await self.detect_faces()
                
                if result.detected:
                    self._last_face_time = time.time()
                    if not self._user_present:
                        self._user_present = True
                        self._trigger_presence_callbacks(True)
                        logger.debug("User presence detected")
                else:
                    if self._user_present:
                        elapsed = time.time() - self._last_face_time
                        if elapsed > self.config.presence_timeout:
                            self._user_present = False
                            self._trigger_presence_callbacks(False)
                            logger.debug("User presence lost")
                            
            except Exception as e:
                logger.error(f"Presence monitor error: {e}")
                
            await asyncio.sleep(1.0)  # Check every second
            
    def _trigger_presence_callbacks(self, present: bool):
        """Rufe alle Presence-Callbacks auf"""
        for callback in self._presence_callbacks:
            try:
                callback(present)
            except Exception as e:
                logger.error(f"Presence callback error: {e}")
                
    def get_status(self) -> dict:
        """Hardware-Status abrufen"""
        return {
            "initialized": self._initialized,
            "camera_active": self._camera is not None and self._camera._running,
            "face_detection_active": self._face_detector is not None,
            "user_present": self._user_present,
            "available_cameras": Camera.list_cameras() if self._initialized else []
        }
        
    async def test_all(self) -> dict:
        """Teste alle Hardware-Komponenten"""
        results = {
            "camera": False,
            "face_detection": False,
            "presence": False
        }
        
        # Test Camera
        if self._camera:
            frame = await self.capture_frame()
            results["camera"] = frame is not None
            
        # Test Face Detection
        if self._face_detector:
            results["face_detection"] = self._face_detector._initialized
            
        # Test Presence
        results["presence"] = self.config.enable_presence
        
        return results
