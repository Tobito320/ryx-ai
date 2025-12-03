"""
Ryx AI - Worker Pool

Manages a pool of operator workers for parallel task execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import threading
import queue
import logging

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """Worker status states"""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class WorkerConfig:
    """Configuration for a worker"""
    id: str
    model: str = "qwen2.5-coder:7b"
    max_concurrent: int = 1
    timeout_seconds: int = 60
    capabilities: List[str] = field(default_factory=list)
    priority: int = 5  # Lower = higher priority


@dataclass
class WorkerTask:
    """A task for a worker to execute"""
    id: str
    action: str
    params: Dict[str, Any]
    callback: Optional[Callable] = None
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 60


@dataclass
class WorkerResult:
    """Result from worker execution"""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    worker_id: str = ""


class Worker:
    """
    A single worker that executes tasks.
    
    Each worker:
    - Has its own task queue
    - Executes tasks sequentially (or concurrently if configured)
    - Reports results via callbacks
    - Can be paused/resumed/stopped
    """
    
    def __init__(
        self,
        config: WorkerConfig,
        tool_executor: Optional[Callable] = None,
        ollama_client = None
    ):
        self.config = config
        self.tool_executor = tool_executor
        self.ollama = ollama_client
        
        self.status = WorkerStatus.IDLE
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._current_task: Optional[WorkerTask] = None
        self._results: List[WorkerResult] = []
        
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Stats
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_time_ms = 0
    
    def start(self):
        """Start the worker thread"""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._pause_event.set()  # Not paused by default
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Worker {self.config.id} started")
    
    def stop(self):
        """Stop the worker"""
        self._stop_event.set()
        self._pause_event.set()  # Unpause to allow exit
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.config.id} stopped")
    
    def pause(self):
        """Pause the worker"""
        self._pause_event.clear()
        self.status = WorkerStatus.PAUSED
        logger.info(f"Worker {self.config.id} paused")
    
    def resume(self):
        """Resume the worker"""
        self._pause_event.set()
        self.status = WorkerStatus.IDLE
        logger.info(f"Worker {self.config.id} resumed")
    
    def submit_task(self, task: WorkerTask) -> bool:
        """Submit a task to this worker"""
        if self.status == WorkerStatus.STOPPED:
            return False
        
        # Priority queue: lower number = higher priority
        self._task_queue.put((task.priority, task.created_at, task))
        return True
    
    def get_queue_size(self) -> int:
        """Get number of queued tasks"""
        return self._task_queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            "id": self.config.id,
            "model": self.config.model,
            "status": self.status.value,
            "queue_size": self.get_queue_size(),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_time_ms": (
                self.total_time_ms / self.tasks_completed 
                if self.tasks_completed > 0 else 0
            ),
            "capabilities": self.config.capabilities,
        }
    
    def _run_loop(self):
        """Main worker loop"""
        while not self._stop_event.is_set():
            # Wait if paused
            self._pause_event.wait()
            
            if self._stop_event.is_set():
                break
            
            try:
                # Get next task (with timeout to check stop event)
                priority, created, task = self._task_queue.get(timeout=1)
                
                self._current_task = task
                self.status = WorkerStatus.BUSY
                
                # Execute task
                result = self._execute_task(task)
                
                # Store result
                self._results.append(result)
                
                # Update stats
                if result.success:
                    self.tasks_completed += 1
                else:
                    self.tasks_failed += 1
                self.total_time_ms += result.duration_ms
                
                # Callback if provided
                if task.callback:
                    try:
                        task.callback(result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                self._current_task = None
                self.status = WorkerStatus.IDLE
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {self.config.id} error: {e}")
                self.status = WorkerStatus.ERROR
    
    def _execute_task(self, task: WorkerTask) -> WorkerResult:
        """Execute a single task"""
        import time
        start = time.time()
        
        try:
            if self.tool_executor:
                # Use provided tool executor
                success, output = self.tool_executor(
                    action=task.action,
                    params=task.params
                )
            else:
                # Default: just return the action
                success = True
                output = f"Executed: {task.action}"
            
            duration_ms = int((time.time() - start) * 1000)
            
            return WorkerResult(
                task_id=task.id,
                success=success,
                output=output,
                duration_ms=duration_ms,
                worker_id=self.config.id
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return WorkerResult(
                task_id=task.id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                worker_id=self.config.id
            )


class WorkerPool:
    """
    Pool of workers for parallel task execution.
    
    Features:
    - Dynamic worker scaling
    - Load balancing across workers
    - Task routing by capability
    - Aggregate statistics
    """
    
    def __init__(
        self,
        min_workers: int = 1,
        max_workers: int = 4,
        tool_executor: Optional[Callable] = None,
        ollama_client = None
    ):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.tool_executor = tool_executor
        self.ollama = ollama_client
        
        self._workers: Dict[str, Worker] = {}
        self._results: List[WorkerResult] = []
        self._lock = threading.Lock()
    
    def start(self, num_workers: Optional[int] = None):
        """Start the worker pool"""
        num = num_workers or self.min_workers
        num = max(self.min_workers, min(self.max_workers, num))
        
        for i in range(num):
            self.add_worker(WorkerConfig(
                id=f"worker_{i}",
                capabilities=["general"]
            ))
        
        logger.info(f"Worker pool started with {num} workers")
    
    def stop(self):
        """Stop all workers"""
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()
        logger.info("Worker pool stopped")
    
    def add_worker(self, config: WorkerConfig) -> bool:
        """Add a new worker to the pool"""
        if len(self._workers) >= self.max_workers:
            return False
        
        if config.id in self._workers:
            return False
        
        worker = Worker(
            config=config,
            tool_executor=self.tool_executor,
            ollama_client=self.ollama
        )
        worker.start()
        
        self._workers[config.id] = worker
        return True
    
    def remove_worker(self, worker_id: str) -> bool:
        """Remove a worker from the pool"""
        if worker_id not in self._workers:
            return False
        
        if len(self._workers) <= self.min_workers:
            return False
        
        worker = self._workers.pop(worker_id)
        worker.stop()
        return True
    
    def submit_task(
        self,
        task: WorkerTask,
        capability: Optional[str] = None
    ) -> Optional[str]:
        """
        Submit a task to the pool.
        
        Returns worker_id that will handle it, or None if no worker available.
        """
        worker = self._select_worker(capability)
        if not worker:
            return None
        
        worker.submit_task(task)
        return worker.config.id
    
    def _select_worker(
        self, 
        capability: Optional[str] = None
    ) -> Optional[Worker]:
        """Select best worker for a task"""
        candidates = list(self._workers.values())
        
        # Filter by capability if specified
        if capability:
            candidates = [
                w for w in candidates 
                if capability in w.config.capabilities or "general" in w.config.capabilities
            ]
        
        # Filter out stopped/error workers
        candidates = [
            w for w in candidates 
            if w.status not in [WorkerStatus.STOPPED, WorkerStatus.ERROR]
        ]
        
        if not candidates:
            return None
        
        # Select by: 1) queue size, 2) priority
        candidates.sort(
            key=lambda w: (w.get_queue_size(), w.config.priority)
        )
        
        return candidates[0]
    
    def get_status(self) -> Dict[str, Any]:
        """Get pool status"""
        workers = [w.get_stats() for w in self._workers.values()]
        
        total_completed = sum(w["tasks_completed"] for w in workers)
        total_failed = sum(w["tasks_failed"] for w in workers)
        total_queued = sum(w["queue_size"] for w in workers)
        
        return {
            "workers": len(self._workers),
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "tasks_queued": total_queued,
            "tasks_completed": total_completed,
            "tasks_failed": total_failed,
            "success_rate": (
                total_completed / (total_completed + total_failed)
                if (total_completed + total_failed) > 0 else 1.0
            ),
            "worker_details": workers,
        }
    
    def scale_up(self, count: int = 1) -> int:
        """Add workers to the pool"""
        added = 0
        for i in range(count):
            worker_id = f"worker_{len(self._workers)}"
            if self.add_worker(WorkerConfig(
                id=worker_id,
                capabilities=["general"]
            )):
                added += 1
        return added
    
    def scale_down(self, count: int = 1) -> int:
        """Remove workers from the pool"""
        removed = 0
        workers = sorted(
            self._workers.values(),
            key=lambda w: w.get_queue_size()
        )
        
        for worker in workers[:count]:
            if self.remove_worker(worker.config.id):
                removed += 1
        
        return removed
