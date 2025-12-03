"""
Ryx AI - Worker Agent

Small, specialized agents that execute tasks assigned by the Supervisor.
Workers use small models (1.5B-3B) for speed and efficiency.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """Types of specialized workers"""
    SEARCH = "search"          # Web search using SearXNG
    SUMMARIZE = "summarize"    # Summarize content
    EXTRACT = "extract"        # Extract specific info
    VALIDATE = "validate"      # Validate/verify info
    GENERAL = "general"        # General purpose


@dataclass
class WorkerTask:
    """Task assigned to a worker"""
    task_id: str
    task_type: WorkerType
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    priority: int = 5  # 1-10, higher = more important


@dataclass
class WorkerResult:
    """Result from a worker"""
    task_id: str
    success: bool
    result: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    model_used: str = ""
    quality_score: float = 0.0  # Set by supervisor


class Worker:
    """
    A single worker agent.
    
    Uses a small model (1.5B-3B) to execute specific tasks quickly.
    Reports results back to the supervisor.
    """
    
    def __init__(
        self,
        worker_id: str,
        model: str,
        worker_type: WorkerType = WorkerType.GENERAL,
        vllm_base_url: str = "http://localhost:8001"
    ):
        self.worker_id = worker_id
        self.model = model
        self.worker_type = worker_type
        self.vllm_base_url = vllm_base_url
        self.busy = False
        self.current_task: Optional[WorkerTask] = None
    
    async def execute(self, task: WorkerTask) -> WorkerResult:
        """
        Execute a task.
        
        Args:
            task: The task to execute
            
        Returns:
            WorkerResult with outcome
        """
        self.busy = True
        self.current_task = task
        start_time = datetime.now()
        
        try:
            # Special handling for search tasks
            if task.task_type == WorkerType.SEARCH:
                result = await self._execute_search(task)
            else:
                result = await self._execute_llm(task)
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                result=result,
                latency_ms=latency,
                model_used=self.model
            )
            
        except asyncio.TimeoutError:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="Timeout",
                model_used=self.model
            )
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}")
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                model_used=self.model
            )
        finally:
            self.busy = False
            self.current_task = None
    
    async def _execute_search(self, task: WorkerTask) -> str:
        """Execute a search task using SearXNG"""
        from .searxng import get_searxng
        
        searxng = get_searxng()
        results = await searxng.search(
            query=task.prompt,
            num_results=task.context.get("num_results", 5)
        )
        
        if not results:
            return "No results found"
        
        # Format results
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r.title}\n    {r.url}\n    {r.content[:200]}...")
        
        return "\n\n".join(formatted)
    
    async def _execute_llm(self, task: WorkerTask) -> str:
        """Execute an LLM task"""
        import aiohttp
        
        # Build system prompt based on worker type
        system_prompts = {
            WorkerType.SUMMARIZE: "Summarize the following content concisely. Focus on key points.",
            WorkerType.EXTRACT: "Extract the specific information requested. Be precise.",
            WorkerType.VALIDATE: "Verify the accuracy of the following. Point out any errors.",
            WorkerType.GENERAL: "Complete the following task efficiently."
        }
        
        system = system_prompts.get(self.worker_type, system_prompts[WorkerType.GENERAL])
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task.prompt}
        ]
        
        if task.context.get("additional_context"):
            messages.insert(1, {
                "role": "system", 
                "content": f"Context: {task.context['additional_context']}"
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.vllm_base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 512
                },
                timeout=aiohttp.ClientTimeout(total=task.timeout)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"]


class WorkerPool:
    """
    Pool of worker agents.
    
    Manages multiple workers, assigns tasks, and handles
    load balancing.
    """
    
    # Available small models for workers
    WORKER_MODELS = [
        "/models/small/general/qwen2.5-3b",
        "/models/small/general/phi-3.5-mini",
        "/models/small/general/gemma-2-2b",
    ]
    
    def __init__(
        self,
        num_workers: int = 5,
        vllm_base_url: str = "http://localhost:8001"
    ):
        self.vllm_base_url = vllm_base_url
        self.workers: List[Worker] = []
        self._task_counter = 0
        
        # Create workers with rotating models
        for i in range(num_workers):
            model = self.WORKER_MODELS[i % len(self.WORKER_MODELS)]
            worker = Worker(
                worker_id=f"worker-{i}",
                model=model,
                vllm_base_url=vllm_base_url
            )
            self.workers.append(worker)
    
    def _get_available_worker(self) -> Optional[Worker]:
        """Get a free worker"""
        for worker in self.workers:
            if not worker.busy:
                return worker
        return None
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        self._task_counter += 1
        return f"task-{self._task_counter}-{datetime.now().strftime('%H%M%S')}"
    
    async def submit(self, task: WorkerTask) -> WorkerResult:
        """
        Submit a single task and wait for result.
        
        Args:
            task: Task to execute
            
        Returns:
            WorkerResult
        """
        worker = self._get_available_worker()
        if not worker:
            # Wait for a worker to become available
            for _ in range(100):  # Max 10 seconds
                await asyncio.sleep(0.1)
                worker = self._get_available_worker()
                if worker:
                    break
        
        if not worker:
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error="No workers available"
            )
        
        return await worker.execute(task)
    
    async def submit_parallel(
        self,
        prompts: List[str],
        task_type: WorkerType = WorkerType.GENERAL,
        context: Dict[str, Any] = None
    ) -> List[WorkerResult]:
        """
        Submit multiple tasks in parallel.
        
        Args:
            prompts: List of prompts to execute
            task_type: Type of task
            context: Shared context
            
        Returns:
            List of WorkerResults
        """
        tasks = []
        for prompt in prompts:
            task = WorkerTask(
                task_id=self._generate_task_id(),
                task_type=task_type,
                prompt=prompt,
                context=context or {}
            )
            tasks.append(task)
        
        # Execute all in parallel
        results = await asyncio.gather(*[
            self.submit(task) for task in tasks
        ])
        
        return list(results)
    
    async def parallel_search(
        self,
        query: str,
        num_searches: int = 3
    ) -> List[WorkerResult]:
        """
        Execute parallel searches with different phrasings.
        
        Args:
            query: Base search query
            num_searches: Number of parallel searches
            
        Returns:
            List of search results
        """
        # Generate search variations
        variations = [
            query,
            f"what is {query}",
            f"{query} explained",
        ][:num_searches]
        
        tasks = []
        for prompt in variations:
            task = WorkerTask(
                task_id=self._generate_task_id(),
                task_type=WorkerType.SEARCH,
                prompt=prompt,
                context={"num_results": 5}
            )
            tasks.append(task)
        
        return await asyncio.gather(*[
            self.submit(task) for task in tasks
        ])
