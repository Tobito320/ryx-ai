# -*- coding: utf-8 -*-
"""
RyxVoice - Voice Input/Output Interface
Spracheingabe und -ausgabe für Ryx

Unterstützt:
- Speech-to-Text (STT) via Whisper (lokal)
- Text-to-Speech (TTS) via Piper/Coqui (lokal)
- Wake-Word Detection via OpenWakeWord
- Voice Activity Detection (VAD)
"""

from .stt import SpeechToText, STTResult, STTConfig
from .tts import TextToSpeech, TTSConfig
from .voice_interface import VoiceInterface, VoiceConfig
from .wake_word import WakeWordDetector, WakeWordConfig

__all__ = [
    'SpeechToText',
    'STTResult',
    'STTConfig',
    'TextToSpeech',
    'TTSConfig',
    'VoiceInterface',
    'VoiceConfig',
    'WakeWordDetector',
    'WakeWordConfig',
]
