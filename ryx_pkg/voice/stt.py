# -*- coding: utf-8 -*-
"""
Speech-to-Text (STT) Module
Lokal via Whisper (faster-whisper für Performance)
"""

import asyncio
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, List
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    """Ergebnis einer Speech-to-Text Transkription"""
    text: str
    language: str = "de"
    confidence: float = 1.0
    duration_seconds: float = 0.0
    segments: List[dict] = field(default_factory=list)
    is_partial: bool = False
    
    def __bool__(self) -> bool:
        return bool(self.text.strip())


@dataclass
class STTConfig:
    """Konfiguration für Speech-to-Text"""
    model: str = "base"  # tiny, base, small, medium, large
    language: str = "de"
    device: str = "auto"  # cpu, cuda, auto
    compute_type: str = "int8"  # float16, int8
    vad_filter: bool = True
    beam_size: int = 5
    
    # Streaming
    enable_streaming: bool = False
    chunk_length_s: float = 5.0


class SpeechToText:
    """
    Speech-to-Text Engine basierend auf Whisper
    
    Unterstützt:
    - faster-whisper (bevorzugt, schneller)
    - whisper.cpp (fallback)
    - OpenAI whisper (fallback)
    """
    
    def __init__(self, config: Optional[STTConfig] = None):
        self.config = config or STTConfig()
        self._model = None
        self._backend: Optional[str] = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialisiere das STT-Modell"""
        if self._initialized:
            return True
            
        # Versuche faster-whisper
        if await self._try_faster_whisper():
            self._backend = "faster-whisper"
            self._initialized = True
            logger.info(f"STT initialized with faster-whisper ({self.config.model})")
            return True
            
        # Fallback: whisper.cpp via CLI
        if await self._check_whisper_cpp():
            self._backend = "whisper-cpp"
            self._initialized = True
            logger.info("STT initialized with whisper.cpp")
            return True
            
        logger.warning("No STT backend available. Install faster-whisper or whisper.cpp")
        return False
        
    async def _try_faster_whisper(self) -> bool:
        """Versuche faster-whisper zu laden"""
        try:
            from faster_whisper import WhisperModel
            
            device = self.config.device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
                    
            self._model = WhisperModel(
                self.config.model,
                device=device,
                compute_type=self.config.compute_type
            )
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning(f"Failed to load faster-whisper: {e}")
            return False
            
    async def _check_whisper_cpp(self) -> bool:
        """Prüfe ob whisper.cpp verfügbar ist"""
        try:
            result = subprocess.run(
                ["whisper-cpp", "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> STTResult:
        """
        Transkribiere Audio-Datei zu Text
        
        Args:
            audio_path: Pfad zur Audio-Datei (wav, mp3, etc.)
            language: Optional - Sprache erzwingen
            
        Returns:
            STTResult mit transkribiertem Text
        """
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized:
            return STTResult(text="", confidence=0.0)
            
        lang = language or self.config.language
        
        if self._backend == "faster-whisper":
            return await self._transcribe_faster_whisper(audio_path, lang)
        elif self._backend == "whisper-cpp":
            return await self._transcribe_whisper_cpp(audio_path, lang)
        else:
            return STTResult(text="", confidence=0.0)
            
    async def _transcribe_faster_whisper(
        self,
        audio_path: Path,
        language: str
    ) -> STTResult:
        """Transkribiere mit faster-whisper"""
        try:
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter
            )
            
            # Sammle alle Segmente
            all_segments = []
            full_text = []
            
            for segment in segments:
                all_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "avg_logprob": segment.avg_logprob
                })
                full_text.append(segment.text)
                
            text = " ".join(full_text).strip()
            
            # Durchschnittliche Confidence
            if all_segments:
                avg_prob = sum(s.get("avg_logprob", 0) for s in all_segments) / len(all_segments)
                confidence = min(1.0, max(0.0, (avg_prob + 1.0) / 0.5))  # Normalisiere logprob
            else:
                confidence = 0.0
                
            return STTResult(
                text=text,
                language=info.language,
                confidence=confidence,
                duration_seconds=info.duration,
                segments=all_segments
            )
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return STTResult(text="", confidence=0.0)
            
    async def _transcribe_whisper_cpp(
        self,
        audio_path: Path,
        language: str
    ) -> STTResult:
        """Transkribiere mit whisper.cpp CLI"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                output_path = Path(f.name)
                
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "whisper-cpp",
                    "-m", f"/usr/share/whisper-cpp/models/ggml-{self.config.model}.bin",
                    "-l", language,
                    "-oj",  # JSON output
                    "-of", str(output_path.with_suffix("")),
                    str(audio_path)
                ],
                capture_output=True,
                timeout=120
            )
            
            if output_path.exists():
                with open(output_path) as f:
                    data = json.load(f)
                    
                text = data.get("transcription", [{}])[0].get("text", "")
                return STTResult(
                    text=text.strip(),
                    language=language,
                    confidence=0.8  # whisper.cpp gibt keine Confidence
                )
            else:
                return STTResult(text="", confidence=0.0)
                
        except Exception as e:
            logger.error(f"whisper.cpp error: {e}")
            return STTResult(text="", confidence=0.0)
        finally:
            if output_path.exists():
                output_path.unlink()
                
    async def transcribe_stream(
        self,
        audio_stream,
        on_partial: Optional[Callable[[STTResult], None]] = None
    ) -> STTResult:
        """
        Streaming-Transkription (für Echtzeit)
        
        Args:
            audio_stream: Generator/AsyncGenerator von Audio-Chunks
            on_partial: Callback für partielle Ergebnisse
            
        Returns:
            Finale STTResult
        """
        if not self.config.enable_streaming:
            raise ValueError("Streaming not enabled in config")
            
        # Sammle Audio in Chunks und transkribiere inkrementell
        chunks = []
        full_text = []
        
        async for chunk in audio_stream:
            chunks.append(chunk)
            
            # Alle chunk_length_s Sekunden transkribieren
            if len(chunks) * 0.1 >= self.config.chunk_length_s:  # Annahme: 100ms chunks
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = Path(f.name)
                    self._save_wav(chunks, temp_path)
                    
                result = await self.transcribe(temp_path)
                temp_path.unlink()
                
                if result and on_partial:
                    result.is_partial = True
                    on_partial(result)
                    
                if result:
                    full_text.append(result.text)
                chunks = []
                
        # Finale Transkription
        if chunks:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = Path(f.name)
                self._save_wav(chunks, temp_path)
                
            result = await self.transcribe(temp_path)
            temp_path.unlink()
            
            if result:
                full_text.append(result.text)
                
        return STTResult(
            text=" ".join(full_text).strip(),
            language=self.config.language,
            confidence=0.8
        )
        
    def _save_wav(self, chunks: List[bytes], path: Path, sample_rate: int = 16000):
        """Speichere Audio-Chunks als WAV"""
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(chunks))
