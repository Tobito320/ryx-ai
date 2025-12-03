"""
Ryx AI - Ollama Client
Production-grade Ollama client with streaming support and error handling

Now with Tool-Call support for structured LLM outputs.
"""

import os
import json
import time
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, Generator, Callable, List, Union
import logging

logger = logging.getLogger(__name__)

# Import tool schema
try:
    from core.tool_schema import (
        ToolCall, ToolCallSequence, ToolCallParser,
        TOOL_ONLY_SYSTEM_PROMPT, get_tool_prompt, get_parser
    )
    TOOL_SCHEMA_AVAILABLE = True
except ImportError:
    TOOL_SCHEMA_AVAILABLE = False


@dataclass
class GenerateResponse:
    """Response from a generate request"""
    response: str
    model: str
    done: bool
    total_duration_ns: Optional[int] = None
    load_duration_ns: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    error: Optional[str] = None
    # Tool call support
    tool_calls: Optional[List[ToolCall]] = None
    is_complete: bool = False


class OllamaClient:
    """
    Production-grade Ollama client

    Features:
    - Streaming support
    - Retry logic with exponential backoff
    - Clean error handling
    - Docker-aware (configurable base URL)
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 60):
        """
        Initialize Ollama client

        Args:
            base_url: Ollama API base URL (defaults to env var or localhost)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get(
            'OLLAMA_BASE_URL',
            os.environ.get('RYX_OLLAMA_URL', 'http://localhost:11434')
        )
        self.timeout = timeout
        self._session = requests.Session()

    def generate(
        self,
        prompt: str,
        model: str = "qwen2.5:3b",
        system: str = "",
        max_tokens: int = 512,
        temperature: float = 0.1,  # Low temperature for focused responses
        stream: bool = False,
        context: Optional[list] = None
    ) -> GenerateResponse:
        """
        Generate a response from the model

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (low = focused)
            stream: Whether to stream the response
            context: Optional conversation context

        Returns:
            GenerateResponse with the generated text
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # We handle streaming separately
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,  # Nucleus sampling for coherence
                "repeat_penalty": 1.1,  # Avoid repetition
            }
        }

        if system:
            payload["system"] = system

        if context:
            payload["context"] = context

        try:
            response = self._request_with_retry(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return GenerateResponse(
                    response=data.get("response", ""),
                    model=data.get("model", model),
                    done=data.get("done", True),
                    total_duration_ns=data.get("total_duration"),
                    load_duration_ns=data.get("load_duration"),
                    prompt_eval_count=data.get("prompt_eval_count"),
                    eval_count=data.get("eval_count")
                )
            else:
                return GenerateResponse(
                    response="",
                    model=model,
                    done=True,
                    error=f"HTTP {response.status_code}: {response.text}"
                )

        except requests.exceptions.ConnectionError as e:
            return GenerateResponse(
                response="",
                model=model,
                done=True,
                error=f"Cannot connect to Ollama at {self.base_url}. Is it running?"
            )
        except requests.exceptions.Timeout:
            return GenerateResponse(
                response="",
                model=model,
                done=True,
                error=f"Request timed out after {self.timeout}s"
            )
        except Exception as e:
            return GenerateResponse(
                response="",
                model=model,
                done=True,
                error=str(e)
            )

    def generate_stream(
        self,
        prompt: str,
        model: str = "qwen2.5-coder:14b",
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        context: Optional[list] = None,
        callback: Optional[Callable[[str], None]] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response from the model

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            context: Optional conversation context
            callback: Optional callback for each chunk

        Yields:
            Text chunks as they are generated
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if system:
            payload["system"] = system

        if context:
            payload["context"] = context

        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout
            )

            if response.status_code != 200:
                yield f"[Error: HTTP {response.status_code}]"
                return

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            if callback:
                                callback(chunk)
                            yield chunk

                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.ConnectionError:
            yield f"[Error: Cannot connect to Ollama at {self.base_url}]"
        except requests.exceptions.Timeout:
            yield f"[Error: Request timed out]"
        except Exception as e:
            yield f"[Error: {str(e)}]"

    def chat(
        self,
        messages: list,
        model: str = "qwen2.5-coder:14b",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        stream: bool = False
    ) -> GenerateResponse:
        """
        Chat with the model using message format

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response

        Returns:
            GenerateResponse with the generated text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = self._request_with_retry(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return GenerateResponse(
                    response=data.get("message", {}).get("content", ""),
                    model=data.get("model", model),
                    done=data.get("done", True),
                    total_duration_ns=data.get("total_duration"),
                    load_duration_ns=data.get("load_duration"),
                    prompt_eval_count=data.get("prompt_eval_count"),
                    eval_count=data.get("eval_count")
                )
            else:
                return GenerateResponse(
                    response="",
                    model=model,
                    done=True,
                    error=f"HTTP {response.status_code}: {response.text}"
                )

        except Exception as e:
            return GenerateResponse(
                response="",
                model=model,
                done=True,
                error=str(e)
            )
    
    def generate_tool_call(
        self,
        task: str,
        model: str = "qwen2.5-coder:14b",
        context: str = "",
        available_files: List[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> GenerateResponse:
        """
        Generate a tool call response from the LLM.
        
        Uses tool-only system prompt to force structured JSON output.
        
        Args:
            task: The task description
            model: Model to use
            context: Additional context (file contents, etc.)
            available_files: List of available files
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (low for structured output)
            
        Returns:
            GenerateResponse with parsed tool_calls
        """
        if not TOOL_SCHEMA_AVAILABLE:
            return GenerateResponse(
                response="",
                model=model,
                done=True,
                error="Tool schema not available"
            )
        
        # Build prompt
        prompt = get_tool_prompt(task, context, available_files)
        
        # Generate with tool-only system prompt
        response = self.generate(
            prompt=prompt,
            model=model,
            system=TOOL_ONLY_SYSTEM_PROMPT,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if response.error:
            return response
        
        # Parse tool calls from response
        parser = get_parser()
        sequence = parser.parse(response.response)
        
        if sequence:
            response.tool_calls = sequence.calls
            response.is_complete = sequence.complete
        else:
            # Parsing failed - still return the raw response
            logger.warning(f"Failed to parse tool calls from: {response.response[:100]}...")
        
        return response

    def list_models(self) -> list:
        """List available models"""
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]

        except Exception as e:
            logger.warning(f"Failed to list models: {e}")

        return []

    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available"""
        return model_name in self.list_models()

    def pull_model(self, model_name: str, progress_callback: Optional[Callable[[dict], None]] = None) -> bool:
        """
        Pull (download) a model

        Args:
            model_name: Name of the model to pull
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful
        """
        try:
            response = self._session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=3600  # Long timeout for large models
            )

            if response.status_code != 200:
                return False

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if progress_callback:
                            progress_callback(data)

                        if data.get("status") == "success":
                            return True

                    except json.JSONDecodeError:
                        continue

            return True

        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs
    ) -> requests.Response:
        """Make a request with retry logic and exponential backoff"""
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._session.request(method, url, **kwargs)

                # Success or client error (no retry)
                if response.status_code < 500:
                    return response

                # Server error - retry with backoff
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"Ollama server error, retrying in {delay}s...")
                    time.sleep(delay)

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"Connection error, retrying in {delay}s...")
                    time.sleep(delay)

        if last_error:
            raise last_error

        return response

    def health_check(self) -> Dict[str, Any]:
        """Check Ollama health"""
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )

            if response.status_code == 200:
                models = response.json().get('models', [])
                return {
                    'status': 'healthy',
                    'models_available': len(models),
                    'base_url': self.base_url
                }
            else:
                return {
                    'status': 'degraded',
                    'error': f"HTTP {response.status_code}",
                    'base_url': self.base_url
                }

        except requests.exceptions.ConnectionError:
            return {
                'status': 'unhealthy',
                'error': f"Cannot connect to {self.base_url}",
                'base_url': self.base_url
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'base_url': self.base_url
            }
