"""
Ryx AI - Task Manager
Manages task state, checkpoints, and graceful interruption handling
"""

import json
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class Checkpoint:
    """A checkpoint in task execution"""
    step: int
    description: str
    data: Dict[str, Any]
    timestamp: str


@dataclass
class Task:
    """A task with state management"""
    id: str
    type: str  # "query", "multi_step", "session"
    description: str
    status: TaskStatus
    created_at: str
    updated_at: str
    
    # Execution state
    current_step: int = 0
    total_steps: int = 1
    checkpoints: List[Checkpoint] = None
    
    # Context
    context: Dict[str, Any] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Model state
    model_used: Optional[str] = None
    loaded_models: List[str] = None
    
    def __post_init__(self):
        if self.checkpoints is None:
            self.checkpoints = []
        if self.context is None:
            self.context = {}
        if self.loaded_models is None:
            self.loaded_models = []


class TaskManager:
    """
    Manages task execution with state persistence:
    - Checkpoint creation for recovery
    - Graceful interruption handling
    - State persistence across restarts
    - Multi-step task coordination
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.home() / "ryx-ai"
        self.state_dir = self.project_root / "data" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Active tasks
        self.active_tasks: Dict[str, Task] = {}
        self.current_task: Optional[Task] = None
        
        # Load persisted state
        self._load_state()
    
    def _load_state(self):
        """Load persisted task state"""
        state_file = self.state_dir / "tasks.json"
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                
                for task_id, task_data in data.items():
                    # Reconstruct checkpoints
                    checkpoints = [
                        Checkpoint(**cp) for cp in task_data.get('checkpoints', [])
                    ]
                    
                    task = Task(
                        id=task_data['id'],
                        type=task_data['type'],
                        description=task_data['description'],
                        status=TaskStatus(task_data['status']),
                        created_at=task_data['created_at'],
                        updated_at=task_data['updated_at'],
                        current_step=task_data.get('current_step', 0),
                        total_steps=task_data.get('total_steps', 1),
                        checkpoints=checkpoints,
                        context=task_data.get('context', {}),
                        result=task_data.get('result'),
                        error=task_data.get('error'),
                        model_used=task_data.get('model_used'),
                        loaded_models=task_data.get('loaded_models', [])
                    )
                    
                    self.active_tasks[task_id] = task
                
                logger.info(f"Loaded {len(self.active_tasks)} persisted tasks")
            except Exception as e:
                logger.error(f"Failed to load task state: {e}")
    
    def _save_state(self):
        """Persist task state to disk"""
        state_file = self.state_dir / "tasks.json"
        
        try:
            data = {}
            for task_id, task in self.active_tasks.items():
                data[task_id] = {
                    'id': task.id,
                    'type': task.type,
                    'description': task.description,
                    'status': task.status.value,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at,
                    'current_step': task.current_step,
                    'total_steps': task.total_steps,
                    'checkpoints': [asdict(cp) for cp in task.checkpoints],
                    'context': task.context,
                    'result': task.result,
                    'error': task.error,
                    'model_used': task.model_used,
                    'loaded_models': task.loaded_models
                }
            
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task state: {e}")
    
    def create_task(self, task_type: str, description: str, 
                   total_steps: int = 1, context: Optional[Dict] = None) -> Task:
        """Create a new task"""
        task_id = f"{task_type}_{int(datetime.now().timestamp() * 1000)}"
        
        task = Task(
            id=task_id,
            type=task_type,
            description=description,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            total_steps=total_steps,
            context=context or {}
        )
        
        self.active_tasks[task_id] = task
        self.current_task = task
        self._save_state()
        
        logger.info(f"Created task: {task_id} - {description}")
        return task
    
    def start_task(self, task_id: str) -> bool:
        """Start task execution"""
        if task_id not in self.active_tasks:
            logger.error(f"Task not found: {task_id}")
            return False
        
        task = self.active_tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now().isoformat()
        self.current_task = task
        
        self._save_state()
        logger.info(f"Started task: {task_id}")
        return True
    
    def checkpoint(self, task_id: str, step: int, description: str, 
                  data: Optional[Dict] = None):
        """Create a checkpoint for recovery"""
        if task_id not in self.active_tasks:
            logger.warning(f"Cannot checkpoint unknown task: {task_id}")
            return
        
        task = self.active_tasks[task_id]
        
        checkpoint = Checkpoint(
            step=step,
            description=description,
            data=data or {},
            timestamp=datetime.now().isoformat()
        )
        
        task.checkpoints.append(checkpoint)
        task.current_step = step
        task.updated_at = datetime.now().isoformat()
        
        self._save_state()
        logger.debug(f"Checkpoint created for {task_id} at step {step}")
    
    def pause_task(self, task_id: str, reason: str = "user_interrupt"):
        """Pause task execution"""
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        
        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.now().isoformat()
            
            # Create pause checkpoint
            self.checkpoint(
                task_id,
                task.current_step,
                f"Paused: {reason}",
                {'pause_reason': reason}
            )
            
            logger.info(f"Paused task: {task_id} - {reason}")
    
    def resume_task(self, task_id: str) -> Optional[Task]:
        """Resume paused task"""
        if task_id not in self.active_tasks:
            logger.error(f"Task not found: {task_id}")
            return None
        
        task = self.active_tasks[task_id]
        
        if task.status != TaskStatus.PAUSED:
            logger.warning(f"Task {task_id} not paused (status: {task.status.value})")
            return None
        
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now().isoformat()
        self.current_task = task
        
        self._save_state()
        logger.info(f"Resumed task: {task_id} from step {task.current_step}")
        return task
    
    def complete_task(self, task_id: str, result: Any = None):
        """Mark task as completed"""
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.now().isoformat()
        
        self._save_state()
        logger.info(f"Completed task: {task_id}")
        
        if self.current_task and self.current_task.id == task_id:
            self.current_task = None
    
    def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error
        task.updated_at = datetime.now().isoformat()
        
        self._save_state()
        logger.error(f"Task failed: {task_id} - {error}")
        
        if self.current_task and self.current_task.id == task_id:
            self.current_task = None
    
    def interrupt_current_task(self, reason: str = "user_interrupt"):
        """Gracefully interrupt current task"""
        if not self.current_task:
            return
        
        task = self.current_task
        task.status = TaskStatus.INTERRUPTED
        task.updated_at = datetime.now().isoformat()
        
        # Create interrupt checkpoint
        self.checkpoint(
            task.id,
            task.current_step,
            f"Interrupted: {reason}",
            {
                'interrupt_reason': reason,
                'can_resume': True
            }
        )
        
        logger.info(f"Interrupted task: {task.id} - {reason}")
    
    def get_resumable_tasks(self) -> List[Task]:
        """Get tasks that can be resumed"""
        return [
            task for task in self.active_tasks.values()
            if task.status in [TaskStatus.PAUSED, TaskStatus.INTERRUPTED]
        ]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.active_tasks.get(task_id)
    
    def get_task_context(self, task_id: str) -> Optional[Dict]:
        """Get task context for recovery"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        # Get most recent checkpoint
        last_checkpoint = task.checkpoints[-1] if task.checkpoints else None
        
        return {
            'task_id': task.id,
            'type': task.type,
            'description': task.description,
            'current_step': task.current_step,
            'total_steps': task.total_steps,
            'last_checkpoint': {
                'step': last_checkpoint.step,
                'description': last_checkpoint.description,
                'data': last_checkpoint.data
            } if last_checkpoint else None,
            'context': task.context,
            'model_used': task.model_used,
            'loaded_models': task.loaded_models
        }
    
    def cleanup_old_tasks(self, days: int = 7):
        """Clean up completed/failed tasks older than N days"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []
        
        for task_id, task in self.active_tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task_time = datetime.fromisoformat(task.updated_at)
                if task_time < cutoff:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
            logger.info(f"Cleaned up old task: {task_id}")
        
        if to_remove:
            self._save_state()
    
    def get_status(self) -> Dict:
        """Get task manager status"""
        status_counts = {status.value: 0 for status in TaskStatus}
        for task in self.active_tasks.values():
            status_counts[task.status.value] += 1
        
        return {
            'total_tasks': len(self.active_tasks),
            'current_task': {
                'id': self.current_task.id,
                'description': self.current_task.description,
                'step': f"{self.current_task.current_step}/{self.current_task.total_steps}",
                'status': self.current_task.status.value
            } if self.current_task else None,
            'resumable_tasks': len(self.get_resumable_tasks()),
            'by_status': status_counts
        }


class InterruptionHandler:
    """
    Handles graceful interruptions (Ctrl+C) with state preservation
    """
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._original_handler = None
    
    def install_handler(self):
        """Install signal handler for Ctrl+C"""
        import signal
        
        def handle_interrupt(signum, frame):
            logger.info("Interrupt signal received (Ctrl+C)")
            
            # Pause current task
            if self.task_manager.current_task:
                self.task_manager.interrupt_current_task("ctrl_c")
                print("\n\n⏸️  Task paused. State saved.")
                print(f"   Task: {self.task_manager.current_task.description}")
                print(f"   Step: {self.task_manager.current_task.current_step}/{self.task_manager.current_task.total_steps}")
                print("\n   Resume with: ryx ::resume")
                print("   Cancel with: ryx ::cancel")
            
            # Exit gracefully
            import sys
            sys.exit(0)
        
        self._original_handler = signal.signal(signal.SIGINT, handle_interrupt)
        logger.debug("Interrupt handler installed")
    
    def restore_handler(self):
        """Restore original signal handler"""
        if self._original_handler:
            import signal
            signal.signal(signal.SIGINT, self._original_handler)
            logger.debug("Interrupt handler restored")
