# -*- coding: utf-8 -*-
"""
Camera Module - Kamera-Integration für Ryx
Unterstützt Webcams, USB-Kameras und Video-Streams
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator, Callable
from pathlib import Path
import logging
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Konfiguration für Kamera"""
    device_id: int = 0  # 0 = Default Webcam
    width: int = 640
    height: int = 480
    fps: int = 30
    backend: str = "auto"  # opencv, v4l2, auto
    mirror: bool = False  # Horizontal spiegeln


@dataclass
class Frame:
    """Ein einzelnes Kamera-Frame"""
    data: bytes  # Raw image data
    width: int
    height: int
    channels: int = 3
    timestamp: float = 0.0
    frame_number: int = 0
    
    def to_numpy(self):
        """Konvertiere zu NumPy Array"""
        try:
            import numpy as np
            return np.frombuffer(self.data, dtype=np.uint8).reshape(
                self.height, self.width, self.channels
            )
        except ImportError:
            raise RuntimeError("numpy required for to_numpy()")


class Camera:
    """
    Kamera-Interface für Ryx
    
    Unterstützt:
    - OpenCV für breite Kompatibilität
    - V4L2 für Linux-native Performance
    - Async Frame-Streaming
    
    Usage:
        camera = Camera()
        await camera.start()
        
        async for frame in camera.stream():
            # Process frame
            process(frame)
            
        await camera.stop()
    """
    
    def __init__(self, config: Optional[CameraConfig] = None):
        self.config = config or CameraConfig()
        self._capture = None
        self._running = False
        self._frame_callback: Optional[Callable[[Frame], None]] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_queue: asyncio.Queue = None
        self._frame_count = 0
        
    async def start(self) -> bool:
        """Starte Kamera-Capture"""
        if self._running:
            return True
            
        try:
            import cv2
            
            self._capture = cv2.VideoCapture(self.config.device_id)
            
            if not self._capture.isOpened():
                logger.error(f"Failed to open camera {self.config.device_id}")
                return False
                
            # Setze Kamera-Parameter
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self._capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Lese tatsächliche Werte
            actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self._capture.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera started: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            self._running = True
            self._frame_queue = asyncio.Queue(maxsize=10)
            
            # Start capture thread
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self._capture_thread.start()
            
            return True
            
        except ImportError:
            logger.error("opencv-python not installed. Run: pip install opencv-python")
            return False
        except Exception as e:
            logger.error(f"Camera start error: {e}")
            return False
            
    async def stop(self):
        """Stoppe Kamera-Capture"""
        self._running = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            
        if self._capture:
            self._capture.release()
            self._capture = None
            
        logger.info("Camera stopped")
        
    def _capture_loop(self):
        """Capture-Loop im separaten Thread"""
        import cv2
        
        while self._running:
            ret, frame = self._capture.read()
            
            if not ret:
                logger.warning("Failed to read frame")
                time.sleep(0.1)
                continue
                
            self._frame_count += 1
            
            # Optional: Spiegeln
            if self.config.mirror:
                frame = cv2.flip(frame, 1)
                
            # Erstelle Frame-Objekt
            frame_obj = Frame(
                data=frame.tobytes(),
                width=frame.shape[1],
                height=frame.shape[0],
                channels=frame.shape[2] if len(frame.shape) > 2 else 1,
                timestamp=time.time(),
                frame_number=self._frame_count
            )
            
            # Callback
            if self._frame_callback:
                try:
                    self._frame_callback(frame_obj)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")
                    
            # Queue für async streaming
            try:
                if self._frame_queue and not self._frame_queue.full():
                    asyncio.get_event_loop().call_soon_threadsafe(
                        self._frame_queue.put_nowait,
                        frame_obj
                    )
            except Exception:
                pass  # Queue nicht bereit
                
            # FPS limiting
            time.sleep(1.0 / self.config.fps)
            
    async def stream(self) -> AsyncIterator[Frame]:
        """Async Generator für Frame-Streaming"""
        if not self._running:
            await self.start()
            
        while self._running:
            try:
                frame = await asyncio.wait_for(
                    self._frame_queue.get(),
                    timeout=1.0
                )
                yield frame
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Stream error: {e}")
                break
                
    async def capture_single(self) -> Optional[Frame]:
        """Einzelnes Frame aufnehmen"""
        if not self._running:
            await self.start()
            
        try:
            return await asyncio.wait_for(
                self._frame_queue.get(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("Capture timeout")
            return None
            
    async def save_snapshot(self, path: Path) -> bool:
        """Speichere Snapshot als Bild"""
        frame = await self.capture_single()
        if not frame:
            return False
            
        try:
            import cv2
            import numpy as np
            
            img = np.frombuffer(frame.data, dtype=np.uint8).reshape(
                frame.height, frame.width, frame.channels
            )
            cv2.imwrite(str(path), img)
            logger.info(f"Snapshot saved: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Snapshot save error: {e}")
            return False
            
    def on_frame(self, callback: Callable[[Frame], None]):
        """Registriere Frame-Callback"""
        self._frame_callback = callback
        
    @staticmethod
    def list_cameras() -> list[dict]:
        """Liste verfügbare Kameras"""
        cameras = []
        
        try:
            import cv2
            
            # Teste Kamera-IDs 0-9
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    cameras.append({
                        "id": i,
                        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                        "fps": int(cap.get(cv2.CAP_PROP_FPS))
                    })
                    cap.release()
        except ImportError:
            pass
            
        return cameras
