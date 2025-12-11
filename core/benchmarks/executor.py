"""
Ryx AI - Benchmark Executor

Connects benchmarks to the LLM backend (Ollama).
This is the bridge between the benchmark system and the inference engine.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .base import Problem
from .runner import RunConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecutorConfig:
    """Configuration for the benchmark executor"""
    backend: str = "ollama"  # ollama, openai
    base_url: str = "http://localhost:11434"
    model: Optional[str] = None
    timeout: int = 120
    
    # Model defaults by backend
    default_models = {
        "ollama": "qwen2.5-coder:14b",
        "openai": "gpt-4",
    }
    
    def get_model(self) -> str:
        return self.model or self.default_models.get(self.backend, "")


class BenchmarkExecutor:
    """
    Executes benchmark problems using an LLM backend.
    
    Usage:
        executor = BenchmarkExecutor(config)
        await executor.connect()
        
        response = await executor.run_problem(problem, run_config)
    """
    
    def __init__(self, config: Optional[ExecutorConfig] = None):
        self.config = config or ExecutorConfig()
        self._client = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to the LLM backend"""
        try:
            if self.config.backend == "ollama":
                from core.ollama_client import OllamaClient
                
                self._client = OllamaClient()
                
                # Test connection
                health = await self._client.health_check()
                if health.get("healthy"):
                    self._connected = True
                    logger.info(f"Connected to Ollama at {self.config.base_url}")
                    return True
                else:
                    logger.error(f"Ollama not healthy: {health}")
                    return False
                
            elif self.config.backend == "openai":
                # OpenAI-compatible API
                self._connected = True
                return True
                
            else:
                logger.error(f"Unknown backend: {self.config.backend}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.backend}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the backend"""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
        self._connected = False
    
    async def run_problem(
        self,
        problem: Problem,
        run_config: RunConfig
    ) -> str:
        """
        Run a benchmark problem through the LLM.
        
        Args:
            problem: The problem to solve
            run_config: Run configuration
            
        Returns:
            The LLM's response
        """
        if not self._connected:
            raise RuntimeError("Not connected to backend. Call connect() first.")
        
        # Build prompt
        prompt = self._build_prompt(problem)
        system = self._get_system_prompt(problem)
        
        try:
            if self.config.backend == "vllm":
                response = await self._client.generate(
                    prompt=prompt,
                    system=system,
                    model=run_config.model or self.config.get_model(),
                    temperature=run_config.temperature,
                    max_tokens=run_config.max_tokens
                )
                
                if response.error:
                    logger.error(f"LLM error: {response.error}")
                    return f"ERROR: {response.error}"
                
                return response.response
                
            elif self.config.backend == "llm":
                return await self._run_llm(prompt, system, run_config)
                
            else:
                return "Backend not implemented"
                
        except asyncio.TimeoutError:
            return "ERROR: Request timed out"
        except Exception as e:
            logger.error(f"Error running problem: {e}")
            return f"ERROR: {e}"
    
    def _build_prompt(self, problem: Problem) -> str:
        """Build the prompt for a problem"""
        return f"""{problem.statement}

Provide ONLY the code solution. No explanations unless specifically asked.
Use markdown code blocks with python syntax highlighting.
"""
    
    def _get_system_prompt(self, problem: Problem) -> str:
        """Get system prompt based on problem category"""
        
        if problem.category.value == "coding":
            return """You are an expert Python programmer.
Write clean, efficient, working code.
Use type hints when appropriate.
Handle edge cases.
Return ONLY the code in a ```python block."""
            
        elif problem.category.value == "fixing":
            return """You are an expert Python debugger.
Analyze the buggy code carefully.
Identify the exact issue.
Provide the FIXED code in a ```python block.
Keep the fix minimal - only change what's necessary."""
            
        else:
            return """You are a helpful coding assistant.
Provide clear, working solutions.
Use ```python code blocks for any code."""
    
    async def _run_llm(
        self,
        prompt: str,
        system: str,
        run_config: RunConfig
    ) -> str:
        """Run via vLLM API"""
        import aiohttp
        
        payload = {
            "model": run_config.model or self.config.get_model(),
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": run_config.temperature,
                "num_predict": run_config.max_tokens,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                else:
                    return f"ERROR: HTTP {resp.status}"


def create_executor(
    backend: str = "vllm",
    base_url: str = "http://localhost:8000",
    model: Optional[str] = None
) -> BenchmarkExecutor:
    """Create a benchmark executor"""
    config = ExecutorConfig(
        backend=backend,
        base_url=base_url,
        model=model
    )
    return BenchmarkExecutor(config)


async def create_connected_executor(
    backend: str = "vllm",
    base_url: str = "http://localhost:8000",
    model: Optional[str] = None
) -> Optional[BenchmarkExecutor]:
    """Create and connect an executor"""
    executor = create_executor(backend, base_url, model)
    if await executor.connect():
        return executor
    return None
