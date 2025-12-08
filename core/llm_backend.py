"""
Ryx AI - LLM Backend

Ollama-first backend for Ryx AI.
Supports both Ollama (default) and vLLM.

Ollama Benefits:
- Multiple models simultaneously
- Auto memory management
- No Docker required
- Better AMD ROCm support
"""

import os
import asyncio
import logging
import threading
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Backend preference (ollama > vllm)
PREFER_OLLAMA = os.environ.get("RYX_BACKEND", "ollama").lower() == "ollama"


@dataclass
class LLMResponse:
    """Unified response from any LLM backend"""
    response: str = ""
    error: Optional[str] = None
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0


class LLMBackend(ABC):
    """Abstract base class for LLM backends"""
    
    @abstractmethod
    def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """Generate a response synchronously"""
        pass
    
    @abstractmethod
    def generate_stream(self, prompt: str, system: str = "", **kwargs) -> Iterator[str]:
        """Generate a response with streaming"""
        pass
    
    async def generate_stream_async(self, prompt: str, system: str = "", **kwargs):
        """Generate a response with async streaming (optional)"""
        # Default implementation for backends without async support
        for token in self.generate_stream(prompt, system, **kwargs):
            yield token
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check if the backend is healthy"""
        pass


class OllamaBackend(LLMBackend):
    """
    Ollama backend - native multi-model support.
    
    Preferred backend for Ryx AI:
    - Loads multiple models as needed
    - Better memory management
    - No Docker required
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = os.environ.get("OLLAMA_HOST", base_url)
        self._client = None
        self._lock = threading.Lock()
    
    def _get_client(self):
        """Get or create Ollama client - thread safe"""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from core.ollama_client import OllamaClient
                    self._client = OllamaClient()
        return self._client
    
    def _run_async(self, coro):
        """Run async code synchronously"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def generate(
        self,
        prompt: str,
        system: str = "",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Generate a response synchronously"""
        
        async def _gen():
            from core.ollama_client import OllamaClient
            client = OllamaClient()
            
            try:
                resp = await client.generate(
                    prompt=prompt,
                    model=model,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return resp
            finally:
                await client.close()
        
        try:
            resp = self._run_async(_gen())
            return LLMResponse(
                response=resp.response,
                error=resp.error,
                model=resp.model,
                tokens_used=resp.tokens_used,
                latency_ms=resp.latency_ms
            )
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return LLMResponse(error=str(e))
    
    def generate_stream(
        self,
        prompt: str,
        system: str = "",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Iterator[str]:
        """Generate with streaming"""
        
        async def _stream_all():
            from core.ollama_client import OllamaClient
            client = OllamaClient()
            tokens = []
            try:
                async for token in client.generate_stream(
                    prompt=prompt,
                    model=model,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    tokens.append(token)
            finally:
                await client.close()
            return tokens
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tokens = loop.run_until_complete(_stream_all())
                for token in tokens:
                    yield token
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"Error: {e}"
    
    async def generate_stream_async(self, prompt: str, system: str = "", model: str = None,
                                   temperature: float = 0.7, max_tokens: int = 4096, **kwargs):
        """Generate with async streaming"""
        from core.ollama_client import OllamaClient
        
        client = OllamaClient()
        try:
            async for token in client.generate_stream(
                prompt=prompt,
                model=model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield token
        finally:
            await client.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check Ollama health"""
        import requests
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "healthy": True,
                    "backend": "ollama",
                    "models": models,
                    "url": self.base_url
                }
            return {"healthy": False, "backend": "ollama", "status": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {
                "healthy": False,
                "backend": "ollama",
                "error": str(e)
            }


def get_backend(prefer_ollama: bool = True) -> LLMBackend:
    """
    Get Ollama backend (vLLM support removed).

    Returns:
        Ollama backend instance
    """
    ollama = OllamaBackend()
    health = ollama.health_check()
    if health.get("healthy"):
        logger.info(f"Using Ollama backend with {len(health.get('models', []))} models")
    else:
        logger.warning("Ollama not running - start with: systemctl --user start ollama")
    return ollama


# Singleton
_backend: Optional[LLMBackend] = None


def get_llm() -> LLMBackend:
    """Get the global LLM backend instance"""
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


def set_backend(backend: LLMBackend):
    """Set the global LLM backend"""
    global _backend
    _backend = backend
