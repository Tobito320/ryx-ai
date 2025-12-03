"""
Ryx AI - Async Multi-Agent Orchestrator

Enables parallel execution of multiple agents with a supervisor coordinating work.
This is a key component for the RSI (Recursive Self-Improvement) system.

Architecture:
- SupervisorAgent: Plans and delegates (uses large model)
- WorkerAgent: Executes tasks (uses fast model)
- ResultCollector: Aggregates results
- FailureHandler: Manages retries and fallbacks
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A task to be executed by a worker"""
    task_id: str
    description: str
    prompt: str
    priority: int = 1  # 1=highest
    timeout: int = 120
    retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskResult:
    """Result from a worker"""
    task_id: str
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0
    retries_used: int = 0


@dataclass
class Worker:
    """A worker that can execute tasks"""
    worker_id: str
    name: str
    status: WorkerStatus = WorkerStatus.IDLE
    current_task: Optional[str] = None
    completed_count: int = 0
    failed_count: int = 0


class AsyncOrchestrator:
    """
    Orchestrates multiple async workers with a supervisor.
    
    Usage:
        orch = AsyncOrchestrator(llm_backend)
        await orch.start()
        
        # Add tasks
        orch.add_task(Task(task_id="1", description="Find files", prompt="..."))
        orch.add_task(Task(task_id="2", description="Read config", prompt="..."))
        
        # Run until all complete
        results = await orch.run_all()
        
        await orch.stop()
    """
    
    def __init__(
        self,
        llm_backend,
        max_workers: int = 3,
        supervisor_model: str = None
    ):
        """
        Args:
            llm_backend: LLM backend for generating responses
            max_workers: Maximum concurrent workers
            supervisor_model: Model for supervisor (if different)
        """
        self.llm = llm_backend
        self.max_workers = max_workers
        self.supervisor_model = supervisor_model
        
        # Task management
        self.pending_tasks: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}
        
        # Workers
        self.workers: List[Worker] = []
        self.worker_tasks: List[asyncio.Task] = []
        
        # Control
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the orchestrator and workers"""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # Create workers
        for i in range(self.max_workers):
            worker = Worker(
                worker_id=f"worker_{i}",
                name=f"Worker-{i}"
            )
            self.workers.append(worker)
            
            # Start worker task
            task = asyncio.create_task(self._worker_loop(worker))
            self.worker_tasks.append(task)
        
        logger.info(f"Orchestrator started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the orchestrator and all workers"""
        if not self._running:
            return
        
        self._running = False
        self._shutdown_event.set()
        
        # Wait for workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.workers.clear()
        self.worker_tasks.clear()
        
        logger.info("Orchestrator stopped")
    
    def add_task(self, task: Task):
        """Add a task to the queue"""
        self.pending_tasks.put_nowait(task)
        logger.debug(f"Added task: {task.task_id}")
    
    async def run_all(self, timeout: int = 600) -> Dict[str, TaskResult]:
        """
        Run all pending tasks and return when complete.
        
        Args:
            timeout: Maximum time to wait for all tasks
            
        Returns:
            Dict of task_id -> TaskResult
        """
        start_time = datetime.now()
        
        while True:
            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                logger.warning(f"Timeout after {elapsed:.1f}s")
                break
            
            # Check if all tasks complete
            if self.pending_tasks.empty() and not self.active_tasks:
                break
            
            await asyncio.sleep(0.5)
        
        return self.completed_tasks.copy()
    
    async def _worker_loop(self, worker: Worker):
        """Main loop for a worker"""
        while self._running:
            try:
                # Wait for task
                try:
                    task = await asyncio.wait_for(
                        self.pending_tasks.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Check dependencies
                if not self._dependencies_met(task):
                    # Re-queue with lower priority
                    await asyncio.sleep(0.5)
                    self.pending_tasks.put_nowait(task)
                    continue
                
                # Execute task
                worker.status = WorkerStatus.WORKING
                worker.current_task = task.task_id
                self.active_tasks[task.task_id] = task
                
                result = await self._execute_task(worker, task)
                
                # Store result
                self.completed_tasks[task.task_id] = result
                del self.active_tasks[task.task_id]
                
                # Update worker stats
                worker.status = WorkerStatus.IDLE
                worker.current_task = None
                if result.success:
                    worker.completed_count += 1
                else:
                    worker.failed_count += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker.worker_id} error: {e}")
                worker.status = WorkerStatus.IDLE
    
    def _dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies are complete"""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
            if not self.completed_tasks[dep_id].success:
                # Dependency failed - this task will also fail
                return False
        return True
    
    async def _execute_task(self, worker: Worker, task: Task) -> TaskResult:
        """Execute a task and return result"""
        start_time = datetime.now()
        retries_used = 0
        
        for attempt in range(task.retries):
            try:
                # Get dependency outputs for context
                dep_context = ""
                for dep_id in task.dependencies:
                    if dep_id in self.completed_tasks:
                        dep_result = self.completed_tasks[dep_id]
                        dep_context += f"\n[{dep_id}]: {dep_result.output[:500]}"
                
                # Build full prompt
                full_prompt = task.prompt
                if dep_context:
                    full_prompt = f"Previous results:{dep_context}\n\nTask: {task.prompt}"
                
                # Call LLM
                response = await self._call_llm_async(full_prompt, task.timeout)
                
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                return TaskResult(
                    task_id=task.task_id,
                    success=True,
                    output=response,
                    duration_ms=duration,
                    retries_used=retries_used
                )
                
            except Exception as e:
                retries_used += 1
                logger.warning(f"Task {task.task_id} attempt {attempt+1} failed: {e}")
                
                if attempt < task.retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        # All retries failed
        duration = (datetime.now() - start_time).total_seconds() * 1000
        return TaskResult(
            task_id=task.task_id,
            success=False,
            error=f"Failed after {task.retries} attempts",
            duration_ms=duration,
            retries_used=retries_used
        )
    
    async def _call_llm_async(self, prompt: str, timeout: int) -> str:
        """Call LLM asynchronously"""
        # Run sync LLM call in thread pool
        loop = asyncio.get_event_loop()
        
        def _call():
            resp = self.llm.generate(prompt, max_tokens=2048, temperature=0.3)
            if hasattr(resp, 'response'):
                return resp.response
            return resp
        
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _call),
            timeout=timeout
        )
        
        return result


class SupervisorOrchestrator(AsyncOrchestrator):
    """
    Enhanced orchestrator with supervisor that plans and delegates.
    
    The supervisor:
    1. Analyzes the user's request
    2. Breaks it into subtasks
    3. Assigns to workers
    4. Monitors progress
    5. Handles failures
    """
    
    SUPERVISOR_PROMPT = '''You are a task planning supervisor.

USER REQUEST: {query}

AVAILABLE WORKERS: {worker_count}

Break this request into parallel subtasks that workers can execute.
Consider dependencies between tasks.

OUTPUT JSON:
{{
    "understanding": "What the user wants",
    "subtasks": [
        {{
            "id": "task_1",
            "description": "What this subtask does",
            "prompt": "Detailed instruction for worker",
            "priority": 1,
            "dependencies": []
        }}
    ],
    "estimated_time_seconds": 30
}}'''
    
    async def plan_and_execute(self, query: str) -> Dict[str, TaskResult]:
        """
        Have supervisor plan the work, then execute it.
        
        Args:
            query: User's request
            
        Returns:
            Results from all subtasks
        """
        # 1. Supervisor creates plan
        logger.info("Supervisor planning...")
        plan = await self._supervisor_plan(query)
        
        if not plan or not plan.get("subtasks"):
            # Single task, execute directly
            self.add_task(Task(
                task_id="main",
                description=query,
                prompt=query
            ))
        else:
            # Add all subtasks
            for subtask in plan["subtasks"]:
                self.add_task(Task(
                    task_id=subtask["id"],
                    description=subtask["description"],
                    prompt=subtask["prompt"],
                    priority=subtask.get("priority", 1),
                    dependencies=subtask.get("dependencies", [])
                ))
        
        # 2. Execute all tasks
        results = await self.run_all()
        
        return results
    
    async def _supervisor_plan(self, query: str) -> Optional[Dict]:
        """Have supervisor create execution plan"""
        prompt = self.SUPERVISOR_PROMPT.format(
            query=query,
            worker_count=self.max_workers
        )
        
        try:
            response = await self._call_llm_async(prompt, timeout=60)
            
            # Parse JSON
            import json
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
            
        except Exception as e:
            logger.error(f"Supervisor planning failed: {e}")
        
        return None


# Convenience function
async def run_parallel_tasks(
    tasks: List[Dict[str, str]],
    llm_backend,
    max_workers: int = 3
) -> Dict[str, TaskResult]:
    """
    Run multiple tasks in parallel.
    
    Args:
        tasks: List of {"id": "...", "prompt": "..."}
        llm_backend: LLM backend
        max_workers: Concurrent workers
        
    Returns:
        Results dict
    """
    orch = AsyncOrchestrator(llm_backend, max_workers=max_workers)
    await orch.start()
    
    for t in tasks:
        orch.add_task(Task(
            task_id=t.get("id", f"task_{len(orch.pending_tasks._queue)}"),
            description=t.get("description", ""),
            prompt=t["prompt"]
        ))
    
    results = await orch.run_all()
    await orch.stop()
    
    return results
