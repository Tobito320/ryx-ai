# -*- coding: utf-8 -*-
"""
Text-to-Speech (TTS) Module
Lokal via Piper oder Coqui TTS
"""

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, AsyncIterator, Callable
import logging
import shutil

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    """Konfiguration für Text-to-Speech"""
    voice: str = "de_DE-thorsten-high"  # Piper voice name
    speed: float = 1.0
    pitch: float = 1.0
    backend: str = "auto"  # piper, coqui, espeak, auto
    output_format: str = "wav"
    sample_rate: int = 22050
    
    # Streaming
    enable_streaming: bool = False
    chunk_size: int = 4096


class TextToSpeech:
    """
    Text-to-Speech Engine
    
    Backends (in Prioritätsreihenfolge):
    1. Piper (schnell, gute Qualität, lokal)
    2. Coqui TTS (hohe Qualität, etwas langsamer)
    3. espeak-ng (Fallback, immer verfügbar auf Linux)
    """
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._backend: Optional[str] = None
        self._initialized = False
        self._piper_model_path: Optional[Path] = None
        
    async def initialize(self) -> bool:
        """Initialisiere TTS-Backend"""
        if self._initialized:
            return True
            
        if self.config.backend == "auto":
            # Auto-detect bestes Backend
            if await self._check_piper():
                self._backend = "piper"
            elif await self._check_coqui():
                self._backend = "coqui"
            elif await self._check_espeak():
                self._backend = "espeak"
            else:
                logger.error("No TTS backend available")
                return False
        else:
            self._backend = self.config.backend
            
        self._initialized = True
        logger.info(f"TTS initialized with {self._backend}")
        return True
        
    async def _check_piper(self) -> bool:
        """Prüfe ob Piper verfügbar ist"""
        try:
            # Prüfe piper binary
            piper_path = shutil.which("piper") or shutil.which("piper-tts")
            if not piper_path:
                return False
                
            # Prüfe ob Voice-Model existiert
            voice_dir = Path.home() / ".local" / "share" / "piper" / "voices"
            model_path = voice_dir / f"{self.config.voice}.onnx"
            
            if model_path.exists():
                self._piper_model_path = model_path
                return True
                
            # Alternativ: System-weite Models
            system_path = Path("/usr/share/piper/voices") / f"{self.config.voice}.onnx"
            if system_path.exists():
                self._piper_model_path = system_path
                return True
                
            logger.info(f"Piper available but voice {self.config.voice} not found")
            return False
            
        except Exception:
            return False
            
    async def _check_coqui(self) -> bool:
        """Prüfe ob Coqui TTS verfügbar ist"""
        try:
            result = subprocess.run(
                ["tts", "--list_models"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    async def _check_espeak(self) -> bool:
        """Prüfe ob espeak-ng verfügbar ist"""
        try:
            result = subprocess.run(
                ["espeak-ng", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    async def synthesize(
        self,
        text: str,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Synthetisiere Text zu Audio
        
        Args:
            text: Zu sprechender Text
            output_path: Optional - Ausgabepfad (sonst temp file)
            
        Returns:
            Pfad zur Audio-Datei
        """
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized:
            return None
            
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=f".{self.config.output_format}"))
            
        if self._backend == "piper":
            return await self._synthesize_piper(text, output_path)
        elif self._backend == "coqui":
            return await self._synthesize_coqui(text, output_path)
        elif self._backend == "espeak":
            return await self._synthesize_espeak(text, output_path)
            
        return None
        
    async def _synthesize_piper(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthese mit Piper"""
        try:
            piper_bin = shutil.which("piper") or shutil.which("piper-tts")
            
            # Piper erwartet Text auf stdin
            process = await asyncio.create_subprocess_exec(
                piper_bin,
                "--model", str(self._piper_model_path),
                "--output_file", str(output_path),
                "--length_scale", str(1.0 / self.config.speed),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.error(f"Piper error: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Piper synthesis error: {e}")
            return None
            
    async def _synthesize_coqui(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthese mit Coqui TTS"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "tts",
                    "--text", text,
                    "--out_path", str(output_path),
                    "--model_name", "tts_models/de/thorsten/tacotron2-DDC"
                ],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.error(f"Coqui error: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Coqui synthesis error: {e}")
            return None
            
    async def _synthesize_espeak(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthese mit espeak-ng (Fallback)"""
        try:
            # espeak-ng kann nur WAV
            wav_path = output_path.with_suffix(".wav")
            
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "espeak-ng",
                    "-v", "de",
                    "-s", str(int(175 * self.config.speed)),
                    "-w", str(wav_path),
                    text
                ],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and wav_path.exists():
                return wav_path
            else:
                logger.error(f"espeak error: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"espeak synthesis error: {e}")
            return None
            
    async def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Sprich Text direkt über Audio-Ausgabe
        
        Args:
            text: Zu sprechender Text
            blocking: Warte bis Ausgabe fertig
            
        Returns:
            True wenn erfolgreich
        """
        audio_path = await self.synthesize(text)
        if not audio_path:
            return False
            
        try:
            # Versuche verschiedene Audio-Player
            players = ["paplay", "aplay", "play", "ffplay"]
            
            for player in players:
                if shutil.which(player):
                    args = [player]
                    
                    if player == "ffplay":
                        args.extend(["-nodisp", "-autoexit"])
                        
                    args.append(str(audio_path))
                    
                    if blocking:
                        result = await asyncio.to_thread(
                            subprocess.run,
                            args,
                            capture_output=True,
                            timeout=60
                        )
                        return result.returncode == 0
                    else:
                        subprocess.Popen(
                            args,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        return True
                        
            logger.warning("No audio player found")
            return False
            
        finally:
            # Cleanup temp file
            if audio_path.exists():
                audio_path.unlink()
                
    async def stream_synthesis(
        self,
        text: str,
        on_chunk: Callable[[bytes], None]
    ) -> bool:
        """
        Streaming-Synthese (für Echtzeit-Ausgabe)
        
        Args:
            text: Zu sprechender Text
            on_chunk: Callback für Audio-Chunks
            
        Returns:
            True wenn erfolgreich
        """
        if not self.config.enable_streaming:
            # Fallback: Normales synthesize + chunks lesen
            audio_path = await self.synthesize(text)
            if not audio_path:
                return False
                
            try:
                with open(audio_path, 'rb') as f:
                    while True:
                        chunk = f.read(self.config.chunk_size)
                        if not chunk:
                            break
                        on_chunk(chunk)
                return True
            finally:
                if audio_path.exists():
                    audio_path.unlink()
                    
        # TODO: Echtes Streaming wenn Backend es unterstützt
        return False
        
    def get_available_voices(self) -> list[str]:
        """Liste verfügbare Stimmen"""
        voices = []
        
        # Piper voices
        voice_dirs = [
            Path.home() / ".local" / "share" / "piper" / "voices",
            Path("/usr/share/piper/voices")
        ]
        
        for voice_dir in voice_dirs:
            if voice_dir.exists():
                for onnx_file in voice_dir.glob("*.onnx"):
                    voices.append(f"piper:{onnx_file.stem}")
                    
        # espeak voices
        try:
            result = subprocess.run(
                ["espeak-ng", "--voices=de"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.decode().strip().split('\n')[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        voices.append(f"espeak:{parts[4]}")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return voices
