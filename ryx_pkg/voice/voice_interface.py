# -*- coding: utf-8 -*-
"""
Voice Interface - Vollständige Voice-Integration für Ryx
Kombiniert STT, TTS und Wake Word Detection
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, AsyncIterator
from pathlib import Path
import logging
import tempfile
import wave

from .stt import SpeechToText, STTConfig, STTResult
from .tts import TextToSpeech, TTSConfig
from .wake_word import WakeWordDetector, WakeWordConfig

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Gesamtkonfiguration für Voice Interface"""
    # STT
    stt_model: str = "base"
    stt_language: str = "de"
    
    # TTS
    tts_voice: str = "de_DE-thorsten-high"
    tts_speed: float = 1.0
    
    # Wake Word
    wake_words: list = field(default_factory=lambda: ["hey_ryx"])
    wake_word_sensitivity: float = 0.5
    
    # General
    enable_wake_word: bool = False
    auto_speak_responses: bool = True
    listen_timeout: float = 10.0
    sample_rate: int = 16000


class VoiceInterface:
    """
    Unified Voice Interface für Ryx
    
    Ermöglicht:
    - Spracheingabe (User spricht, Ryx versteht)
    - Sprachausgabe (Ryx spricht Antworten)
    - Wake Word Aktivierung ("Hey Ryx")
    - Voice Activity Detection
    
    Usage:
        voice = VoiceInterface()
        await voice.initialize()
        
        # Höre auf Eingabe
        result = await voice.listen()
        print(result.text)
        
        # Sprich Antwort
        await voice.speak("Ich habe verstanden!")
        
        # Wake Word Mode
        voice.on_wake_word(handle_activation)
        await voice.start_wake_word_listening()
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        
        # Sub-components
        self.stt = SpeechToText(STTConfig(
            model=self.config.stt_model,
            language=self.config.stt_language
        ))
        
        self.tts = TextToSpeech(TTSConfig(
            voice=self.config.tts_voice,
            speed=self.config.tts_speed
        ))
        
        self.wake_word = WakeWordDetector(WakeWordConfig(
            wake_words=self.config.wake_words,
            sensitivity=self.config.wake_word_sensitivity
        ))
        
        self._initialized = False
        self._is_listening = False
        self._wake_word_callbacks: list = []
        
    async def initialize(self) -> bool:
        """Initialisiere alle Voice-Komponenten"""
        if self._initialized:
            return True
            
        stt_ok = await self.stt.initialize()
        tts_ok = await self.tts.initialize()
        
        if self.config.enable_wake_word:
            await self.wake_word.initialize()
            self.wake_word.on_wake_word(self._handle_wake_word)
            
        self._initialized = stt_ok or tts_ok
        
        status = []
        if stt_ok:
            status.append("STT")
        if tts_ok:
            status.append("TTS")
        if self.config.enable_wake_word:
            status.append("WakeWord")
            
        logger.info(f"Voice interface initialized: {', '.join(status)}")
        return self._initialized
        
    async def listen(
        self,
        timeout: Optional[float] = None,
        on_partial: Optional[Callable[[STTResult], None]] = None
    ) -> STTResult:
        """
        Höre auf Spracheingabe und transkribiere
        
        Args:
            timeout: Max. Wartezeit in Sekunden
            on_partial: Callback für partielle Ergebnisse
            
        Returns:
            STTResult mit transkribiertem Text
        """
        if not self._initialized:
            await self.initialize()
            
        timeout = timeout or self.config.listen_timeout
        
        try:
            import pyaudio
            import numpy as np
        except ImportError:
            logger.error("pyaudio not installed. Run: pip install pyaudio")
            return STTResult(text="", confidence=0.0)
            
        self._is_listening = True
        logger.debug("Listening for speech...")
        
        try:
            # Audio Recording
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            frames = []
            silence_frames = 0
            has_speech = False
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.debug("Listen timeout")
                    break
                    
                # Read audio
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                except Exception:
                    continue
                    
                frames.append(data)
                
                # Voice Activity Detection (simple energy-based)
                audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                energy = np.sqrt(np.mean(audio_array ** 2))
                
                if energy > 500:  # Speech detected
                    has_speech = True
                    silence_frames = 0
                else:
                    if has_speech:
                        silence_frames += 1
                        # ~1.5s Stille nach Sprache = Ende
                        if silence_frames > 25:
                            break
                            
                # Prevent blocking event loop
                await asyncio.sleep(0.01)
                
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
            if not has_speech or len(frames) < 10:
                logger.debug("No speech detected")
                return STTResult(text="", confidence=0.0)
                
            # Save to temp file and transcribe
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = Path(f.name)
                
            with wave.open(str(temp_path), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.config.sample_rate)
                wav.writeframes(b''.join(frames))
                
            result = await self.stt.transcribe(temp_path)
            temp_path.unlink()
            
            if result:
                logger.info(f"Transcribed: {result.text[:50]}...")
                
            return result
            
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return STTResult(text="", confidence=0.0)
        finally:
            self._is_listening = False
            
    async def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Sprich Text über Audio-Ausgabe
        
        Args:
            text: Zu sprechender Text
            blocking: Warte bis Ausgabe fertig
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized:
            await self.initialize()
            
        if not text.strip():
            return True
            
        logger.debug(f"Speaking: {text[:50]}...")
        return await self.tts.speak(text, blocking=blocking)
        
    async def conversation_turn(
        self,
        process_input: Callable[[str], str]
    ) -> tuple[str, str]:
        """
        Führe einen Gesprächszug durch:
        1. Höre auf User
        2. Verarbeite mit callback
        3. Sprich Antwort
        
        Args:
            process_input: Callback für Input-Verarbeitung
            
        Returns:
            Tuple (user_input, response)
        """
        # Listen
        result = await self.listen()
        if not result:
            return "", ""
            
        user_input = result.text
        
        # Process
        response = process_input(user_input)
        
        # Speak
        if self.config.auto_speak_responses:
            await self.speak(response)
            
        return user_input, response
        
    def on_wake_word(self, callback: Callable[[str], None]):
        """Registriere Callback für Wake Word Detection"""
        self._wake_word_callbacks.append(callback)
        
    async def start_wake_word_listening(self):
        """Starte Wake Word Detection"""
        if not self.config.enable_wake_word:
            logger.warning("Wake word not enabled in config")
            return
            
        await self.wake_word.start_listening()
        
    def stop_wake_word_listening(self):
        """Stoppe Wake Word Detection"""
        self.wake_word.stop_listening()
        
    def _handle_wake_word(self, wake_word: str):
        """Interner Handler für Wake Word Detection"""
        logger.info(f"Wake word activated: {wake_word}")
        for callback in self._wake_word_callbacks:
            try:
                callback(wake_word)
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")
                
    @property
    def is_listening(self) -> bool:
        """Prüfe ob gerade gehört wird"""
        return self._is_listening
        
    def get_available_voices(self) -> list[str]:
        """Liste verfügbare TTS-Stimmen"""
        return self.tts.get_available_voices()
        
    async def test(self) -> dict:
        """Teste Voice-Funktionalität"""
        results = {
            "stt": False,
            "tts": False,
            "wake_word": False
        }
        
        # Test TTS
        try:
            audio_path = await self.tts.synthesize("Test der Sprachausgabe")
            if audio_path and audio_path.exists():
                results["tts"] = True
                audio_path.unlink()
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            
        # Test STT (nur check ob initialisiert)
        results["stt"] = self.stt._initialized
        
        # Test Wake Word (nur check ob initialisiert)
        results["wake_word"] = self.config.enable_wake_word
        
        return results
