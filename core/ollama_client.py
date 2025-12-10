"""
Ryx AI - Ollama Client

Native Ollama client for Ryx AI.
Replaces vLLM with Ollama for flexible multi-model usage.

Benefits over vLLM:
- Load multiple models (no single-model limitation)
- Auto memory management (loads/unloads as needed)
- Simpler setup (no Docker required)
- Better AMD ROCm support out of the box
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

OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class OllamaResponse:
    """Response from Ollama API"""
    response: str = ""
    error: Optional[str] = None
    model: str = ""
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    done: bool = True


@dataclass
class OllamaConfig:
    """Configuration for Ollama client"""
    base_url: str = OLLAMA_BASE_URL
    timeout: int = 300  # Ollama can be slow on first load
    
    # Model mapping by task - Optimized 2024-12-10
    models: Dict[str, str] = field(default_factory=lambda: {
        # Fast tasks (1.5B - instant)
        "fast": "qwen2.5:1.5b",
        "intent": "qwen2.5:1.5b",
        
        # Chat (3B - quick and good)
        "chat": "qwen2.5:3b",
        "general": "qwen2.5:3b",
        "uncensored": "dolphin-mistral:7b",
        
        # Coding (main workhorse - 14B, best at 88.4% HumanEval)
        "code": "qwen2.5-coder:14b",
        "coder": "qwen2.5-coder:14b",
        "code_fast": "qwen2.5-coder:7b",
        
        # Reasoning (phi4 - better than deepseek-r1)
        "reason": "phi4",
        "think": "phi4",
        "plan": "phi4",
        
        # Embeddings
        "embed": "nomic-embed-text:latest",
        
        # Default - use 7B coder for balance of speed/quality
        "default": "qwen2.5-coder:7b",
    })


class OllamaClient:
    """
    Async-first Ollama client for Ryx AI.
    
    Key features:
    - Multiple models simultaneously
    - Automatic model loading
    - True streaming support
    - OpenAI-compatible chat format
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
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
    
    def resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to actual model name"""
        if model is None:
            return self.config.models.get("default", "qwen2.5:7b")
        # Check if it's an alias
        return self.config.models.get(model, model)
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> OllamaResponse:
        """
        Generate completion using Ollama /api/generate endpoint.
        """
        model = self.resolve_model(model)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    error_text = await resp.text()
                    return OllamaResponse(
                        error=f"HTTP {resp.status}: {error_text}",
                        model=model
                    )
                
                data = await resp.json()
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                return OllamaResponse(
                    response=data.get("response", ""),
                    model=model,
                    tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    latency_ms=latency,
                    done=data.get("done", True)
                )
                
        except asyncio.TimeoutError:
            return OllamaResponse(error="Request timeout", model=model)
        except aiohttp.ClientError as e:
            return OllamaResponse(error=f"Connection error: {e}", model=model)
        except Exception as e:
            return OllamaResponse(error=f"Unexpected error: {e}", model=model)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> OllamaResponse:
        """
        Chat completion using Ollama /api/chat endpoint.
        OpenAI-compatible message format.
        """
        model = self.resolve_model(model)
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    error_text = await resp.text()
                    return OllamaResponse(
                        error=f"HTTP {resp.status}: {error_text}",
                        model=model
                    )
                
                if stream:
                    # Handle streaming
                    full_response = ""
                    async for line in resp.content:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            content = data.get("message", {}).get("content", "")
                            full_response += content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                    
                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    return OllamaResponse(
                        response=full_response,
                        model=model,
                        latency_ms=latency
                    )
                else:
                    data = await resp.json()
                    latency = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return OllamaResponse(
                        response=data.get("message", {}).get("content", ""),
                        model=model,
                        tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                        prompt_tokens=data.get("prompt_eval_count", 0),
                        completion_tokens=data.get("eval_count", 0),
                        latency_ms=latency,
                        done=data.get("done", True)
                    )
                    
        except asyncio.TimeoutError:
            return OllamaResponse(error="Request timeout", model=model)
        except aiohttp.ClientError as e:
            return OllamaResponse(error=f"Connection error: {e}", model=model)
        except Exception as e:
            return OllamaResponse(error=f"Unexpected error: {e}", model=model)
    
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream tokens as they're generated.
        """
        model = self.resolve_model(model)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    error_text = await resp.text()
                    yield f"[ERROR: HTTP {resp.status}]"
                    return
                
                async for line in resp.content:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield f"[ERROR: {e}]"
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream chat completion tokens.
        """
        model = self.resolve_model(model)
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                
                if resp.status != 200:
                    yield f"[ERROR: HTTP {resp.status}]"
                    return
                
                async for line in resp.content:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield f"[ERROR: {e}]"
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models"""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("models", [])
                return []
                
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": False}
            ) as resp:
                return resp.status == 200
                
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama is running"""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "healthy": True,
                        "backend": "ollama",
                        "models": models,
                        "url": self.base_url
                    }
                return {"healthy": False, "status": f"HTTP {resp.status}"}
                
        except Exception as e:
            return {"healthy": False, "backend": "ollama", "error": str(e)}
    
    # Synchronous wrappers
    
    def generate_sync(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> OllamaResponse:
        """Synchronous wrapper for generate()"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.generate(prompt, model, system, **kwargs)
            )
        finally:
            loop.close()
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> OllamaResponse:
        """Synchronous wrapper for chat()"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.chat(messages, model, **kwargs)
            )
        finally:
            loop.close()


# Singleton
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client singleton"""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
