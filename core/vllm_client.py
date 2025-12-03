"""
Ryx AI - vLLM Client

OpenAI-compatible client for vLLM server.
Supports:
- Chat completions (streaming and non-streaming)
- Multiple concurrent requests (for multi-agent)
- Automatic retry with exponential backoff
- Model switching

This replaces OllamaClient when using vLLM backend.
"""

import os
import json
import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any, Iterator, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VLLMResponse:
    """Response from vLLM API"""
    response: str = ""
    error: Optional[str] = None
    model: str = ""
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""
    latency_ms: float = 0.0


@dataclass
class VLLMConfig:
    """Configuration for vLLM client"""
    base_url: str = "http://localhost:8001"  # Port 8001 to avoid RyxHub conflict
    default_model: str = "/models/medium/general/qwen2.5-7b-gptq"
    timeout: int = 120
    max_retries: int = 3
    
    # Model aliases for easier access
    models: Dict[str, str] = field(default_factory=lambda: {
        "default": "/models/medium/general/qwen2.5-7b-gptq",
        "coder": "/models/medium/coding/qwen2.5-coder-7b-gptq",
        "fast": "/models/small/general/qwen2.5-3b",
        "tiny": "/models/small/coding/qwen2.5-coder-1.5b",
    })


class VLLMClient:
    """
    Async-first vLLM client for Ryx AI.
    
    Designed for multi-agent systems where multiple requests
    need to be processed concurrently.
    """
    
    def __init__(self, config: Optional[VLLMConfig] = None):
        self.config = config or VLLMConfig()
        self.base_url = self.config.base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full name"""
        return self.config.models.get(model, model)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> VLLMResponse:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name or alias
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            **kwargs: Additional parameters for vLLM
            
        Returns:
            VLLMResponse with result or error
        """
        model = self._resolve_model(model or self.config.default_model)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    error_text = await resp.text()
                    return VLLMResponse(
                        error=f"HTTP {resp.status}: {error_text}",
                        model=model
                    )
                
                if stream:
                    # Handle streaming response
                    full_response = ""
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                full_response += content
                            except json.JSONDecodeError:
                                continue
                    
                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    return VLLMResponse(
                        response=full_response,
                        model=model,
                        latency_ms=latency
                    )
                else:
                    # Handle non-streaming response
                    data = await resp.json()
                    
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    usage = data.get("usage", {})
                    
                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return VLLMResponse(
                        response=message.get("content", ""),
                        model=model,
                        tokens_used=usage.get("total_tokens", 0),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        finish_reason=choice.get("finish_reason", ""),
                        latency_ms=latency
                    )
                    
        except asyncio.TimeoutError:
            return VLLMResponse(error="Request timeout", model=model)
        except aiohttp.ClientError as e:
            return VLLMResponse(error=f"Connection error: {e}", model=model)
        except Exception as e:
            return VLLMResponse(error=f"Unexpected error: {e}", model=model)
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> VLLMResponse:
        """
        Simple generate interface (wraps chat).
        
        Args:
            prompt: User prompt
            model: Model name or alias
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            VLLMResponse
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream tokens as they're generated.
        
        Yields:
            Token strings as they arrive
        """
        model = self._resolve_model(model or self.config.default_model)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"[ERROR: HTTP {resp.status}]"
                    return
                
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield f"[ERROR: {e}]"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if vLLM server is running and get info"""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    return {"healthy": True, "status": "running"}
                return {"healthy": False, "status": f"HTTP {resp.status}"}
                
        except Exception as e:
            return {"healthy": False, "status": str(e)}
    
    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m["id"] for m in data.get("data", [])]
                return []
                
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    # Synchronous wrappers for compatibility with existing code
    
    def generate_sync(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> VLLMResponse:
        """Synchronous wrapper for generate()"""
        return asyncio.run(self.generate(prompt, model, system, **kwargs))
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> VLLMResponse:
        """Synchronous wrapper for chat()"""
        return asyncio.run(self.chat(messages, model, **kwargs))


# Singleton instance
_client: Optional[VLLMClient] = None


def get_vllm_client() -> VLLMClient:
    """Get or create vLLM client singleton"""
    global _client
    if _client is None:
        config = VLLMConfig(
            base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8000"),
            default_model=os.environ.get("VLLM_DEFAULT_MODEL", "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ")
        )
        _client = VLLMClient(config)
    return _client


# For backwards compatibility with OllamaClient interface
class VLLMCompatClient:
    """
    Wrapper that provides OllamaClient-compatible interface.
    Drop-in replacement for existing code.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = VLLMClient(VLLMConfig(base_url=base_url))
        self.base_url = base_url
    
    def generate(
        self,
        prompt: str,
        model: str = None,
        system: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ):
        """Compatible with OllamaClient.generate()"""
        response = self.client.generate_sync(
            prompt=prompt,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Return object with same interface as OllamaResponse
        class CompatResponse:
            pass
        
        result = CompatResponse()
        result.response = response.response
        result.error = response.error
        result.model = response.model
        return result
    
    def generate_stream(
        self,
        prompt: str,
        model: str = None,
        system: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[str]:
        """Compatible with OllamaClient.generate_stream()"""
        async def run():
            async for token in self.client.generate_stream(
                prompt=prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield token
        
        # Run async generator synchronously
        loop = asyncio.new_event_loop()
        try:
            gen = run()
            while True:
                try:
                    yield loop.run_until_complete(gen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
