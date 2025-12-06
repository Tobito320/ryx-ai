"""
Ryx AI - LLM Backend

vLLM-only backend for Ryx AI.
Provides sync interface over async vLLM client.
"""

import os
import asyncio
import logging
import threading
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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


class VLLMBackend(LLMBackend):
    """
    vLLM backend - wraps VLLMClient with sync interface for brain.
    
    Uses asyncio.run() internally to provide sync interface.
    """
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        from core.vllm_client import VLLMClient, VLLMConfig
        
        self.base_url = base_url
        self.config = VLLMConfig(base_url=base_url)
        self._client = None
        self._lock = threading.Lock()
    
    def _get_client(self):
        """Get or create the vLLM client - thread safe"""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from core.vllm_client import VLLMClient
                    self._client = VLLMClient(self.config)
        return self._client
    
    def _run_async(self, coro):
        """Run async code synchronously - thread safe"""
        # Always create new event loop for thread safety
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
        max_tokens: int = 2048,
        **kwargs
    ) -> LLMResponse:
        """Generate a response synchronously"""
        
        async def _gen():
            # Create new client for this call (thread-safe)
            from core.vllm_client import VLLMClient
            client = VLLMClient(self.config)
            
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                resp = await client.chat(
                    messages=messages,
                    model=model,
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
            logger.error(f"vLLM generate error: {e}")
            return LLMResponse(error=str(e))
    
    def generate_stream(
        self,
        prompt: str,
        system: str = "",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Iterator[str]:
        """Generate a response with TRUE token-by-token streaming"""
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Use true async streaming with a single event loop
        async def _stream_all():
            from core.vllm_client import VLLMClient
            client = VLLMClient(self.config)
            tokens = []
            try:
                async for token in client.generate_stream(
                    prompt=prompt,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    tokens.append(token)
            finally:
                await client.close()
            return tokens
        
        try:
            # Create a single event loop for the entire stream
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tokens = loop.run_until_complete(_stream_all())
                for token in tokens:
                    yield token
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"vLLM stream error: {e}")
            yield f"Error: {e}"
    
    async def generate_stream_async(self, prompt: str, system: str = "", model: str = None, 
                                   temperature: float = 0.7, max_tokens: int = 2048, **kwargs):
        """Generate a response with async streaming - native async version"""
        from core.vllm_client import VLLMClient
        
        client = VLLMClient(self.config)
        try:
            async for token in client.generate_stream(
                prompt=prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield token
        finally:
            await client.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Check vLLM health"""
        import requests
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return {
                "healthy": resp.status_code == 200,
                "backend": "vllm",
                "url": self.base_url
            }
        except Exception as e:
            return {
                "healthy": False,
                "backend": "vllm",
                "error": str(e)
            }


def get_backend(prefer_vllm: bool = True) -> LLMBackend:
    """
    Get the vLLM backend.
    
    Returns:
        An LLM backend instance (vLLM only)
    """
    vllm = VLLMBackend()
    health = vllm.health_check()
    if health.get("healthy"):
        logger.info("Using vLLM backend")
        return vllm
    
    # vLLM not running - return anyway, will be started when needed
    logger.warning("vLLM not running - start with: ryx")
    return vllm


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
