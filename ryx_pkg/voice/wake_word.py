# -*- coding: utf-8 -*-
"""
Wake Word Detection Module
Erkennt Aktivierungswörter wie "Hey Ryx"
"""

import asyncio
import threading
from dataclasses import dataclass
from typing import Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Konfiguration für Wake Word Detection"""
    wake_words: List[str] = None  # ["hey_ryx", "ryx"]
    sensitivity: float = 0.5  # 0.0-1.0
    backend: str = "auto"  # openwakeword, porcupine, auto
    sample_rate: int = 16000
    
    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = ["hey_ryx"]


class WakeWordDetector:
    """
    Wake Word Detection für Hands-free Aktivierung
    
    Backends:
    1. OpenWakeWord (Open Source, lokal)
    2. Porcupine (Picovoice, benötigt API Key)
    3. Simple Energy-based (Fallback)
    """
    
    def __init__(self, config: Optional[WakeWordConfig] = None):
        self.config = config or WakeWordConfig()
        self._backend: Optional[str] = None
        self._detector = None
        self._running = False
        self._callbacks: List[Callable[[str], None]] = []
        self._audio_thread: Optional[threading.Thread] = None
        
    async def initialize(self) -> bool:
        """Initialisiere Wake Word Detector"""
        if self.config.backend == "auto":
            if await self._try_openwakeword():
                self._backend = "openwakeword"
            else:
                logger.warning("No wake word backend available. Using energy-based fallback.")
                self._backend = "energy"
        else:
            self._backend = self.config.backend
            
        logger.info(f"Wake word detector initialized with {self._backend}")
        return True
        
    async def _try_openwakeword(self) -> bool:
        """Versuche OpenWakeWord zu laden"""
        try:
            from openwakeword.model import Model
            
            # Lade Modell für Wake Words
            self._detector = Model(
                wakeword_models=self.config.wake_words,
                inference_framework="onnx"
            )
            return True
        except ImportError:
            logger.info("openwakeword not installed")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize openwakeword: {e}")
            return False
            
    def on_wake_word(self, callback: Callable[[str], None]):
        """Registriere Callback für Wake Word Detection"""
        self._callbacks.append(callback)
        
    async def start_listening(self):
        """Starte Wake Word Listening im Hintergrund"""
        if self._running:
            return
            
        self._running = True
        
        if self._backend == "openwakeword":
            self._audio_thread = threading.Thread(
                target=self._listen_loop_openwakeword,
                daemon=True
            )
        else:
            self._audio_thread = threading.Thread(
                target=self._listen_loop_energy,
                daemon=True
            )
            
        self._audio_thread.start()
        logger.info("Wake word listening started")
        
    def stop_listening(self):
        """Stoppe Wake Word Listening"""
        self._running = False
        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)
        logger.info("Wake word listening stopped")
        
    def _listen_loop_openwakeword(self):
        """Listening Loop mit OpenWakeWord"""
        try:
            import pyaudio
            import numpy as np
            
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=1280  # 80ms bei 16kHz
            )
            
            while self._running:
                audio_data = stream.read(1280, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Predict
                prediction = self._detector.predict(audio_array)
                
                for wake_word in self.config.wake_words:
                    score = prediction.get(wake_word, 0)
                    if score > self.config.sensitivity:
                        logger.info(f"Wake word detected: {wake_word} (score: {score:.2f})")
                        self._trigger_callbacks(wake_word)
                        
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
        except ImportError:
            logger.error("pyaudio not installed for wake word detection")
        except Exception as e:
            logger.error(f"Wake word listening error: {e}")
            
    def _listen_loop_energy(self):
        """Einfacher Energy-basierter Wake Word Detector (Fallback)"""
        try:
            import pyaudio
            import numpy as np
            
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            # Rolling energy tracking
            energy_history = []
            triggered = False
            silence_frames = 0
            
            while self._running:
                audio_data = stream.read(1024, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                
                # Berechne Energie
                energy = np.sqrt(np.mean(audio_array ** 2))
                energy_history.append(energy)
                
                if len(energy_history) > 50:
                    energy_history.pop(0)
                    
                avg_energy = np.mean(energy_history)
                threshold = avg_energy * 2.0  # Dynamischer Threshold
                
                if energy > threshold and energy > 500:  # Mindestenergie
                    if not triggered:
                        triggered = True
                        silence_frames = 0
                        logger.debug(f"Speech detected (energy: {energy:.0f})")
                else:
                    if triggered:
                        silence_frames += 1
                        if silence_frames > 10:  # ~640ms Stille
                            triggered = False
                            self._trigger_callbacks("voice_activity")
                            
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
        except ImportError:
            logger.error("pyaudio not installed")
        except Exception as e:
            logger.error(f"Energy detection error: {e}")
            
    def _trigger_callbacks(self, wake_word: str):
        """Rufe alle registrierten Callbacks auf"""
        for callback in self._callbacks:
            try:
                callback(wake_word)
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")
