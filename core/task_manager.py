"""
Ryx AI V2 - Task Manager
State persistence and graceful interrupt handling for complex tasks
"""

import json
import signal
import sqlite3
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskStep:
    """A step in a multi-step task"""
    step_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

@dataclass
class Task:
    """A task that can be checkpointed and resumed"""
    task_id: str
    description: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    steps: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None

class TaskManager:
    """
    Manages task execution with state persistence and recovery

    Features:
    - State Persistence: Survives crashes and interrupts
    - Checkpoint System: Can resume from any point
    - Graceful Ctrl+C: Saves state instead of crashing
    - Task Resume: Continue interrupted tasks
    - Multi-Step Coordination: Handle complex tasks with multiple steps
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = get_project_root() / "data" / "task_manager.db"

        self.db_path = db_path
        self.current_task: Optional[Task] = None

        self._init_db()

    def _init_db(self):
        """Initialize task management database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                paused_at TEXT,
                current_step_index INTEGER DEFAULT 0,
                metadata TEXT,
                result TEXT,
                error TEXT
            )
        """)

        # Task steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)

        conn.commit()
        conn.close()

    def create_task(self, description: str, steps: Optional[List[str]] = None) -> Task:
        """
        Create a new task

        Args:
            description: Task description
            steps: Optional list of step descriptions

        Returns:
            Task object
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        task = Task(
            task_id=task_id,
            description=description,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        # Add steps if provided
        if steps:
            for i, step_desc in enumerate(steps):
                step = TaskStep(
                    step_id=f"step_{i+1}",
                    description=step_desc
                )
                task.steps.append(step)

        self._save_task(task)
        return task

    def start_task(self, task: Task):
        """Start executing a task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.current_task = task
        self._save_task(task)

    def pause_task(self, task: Task):
        """Pause a running task"""
        task.status = TaskStatus.PAUSED
        task.paused_at = datetime.now()
        self._save_task(task)

    def resume_task(self, task_id: str) -> Optional[Task]:
        """
        Resume a paused task

        Returns:
            Task if found and resumable, None otherwise
        """
        task = self._load_task(task_id)

        if task and task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.RUNNING
            task.paused_at = None
            self.current_task = task
            self._save_task(task)
            return task

        return None

    def complete_task(self, task: Task, result: Any = None):
        """Mark task as completed"""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.result = result
        self.current_task = None
        self._save_task(task)

    def fail_task(self, task: Task, error: str):
        """Mark task as failed"""
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()
        task.error = error
        self.current_task = None
        self._save_task(task)

    def start_step(self, task: Task, step_index: int):
        """Start a specific step"""
        if step_index < len(task.steps):
            step = task.steps[step_index]
            step.status = TaskStatus.RUNNING
            step.started_at = datetime.now()
            task.current_step_index = step_index
            self._save_task(task)

    def complete_step(self, task: Task, step_index: int, result: Any = None):
        """Complete a step"""
        if step_index < len(task.steps):
            step = task.steps[step_index]
            step.status = TaskStatus.COMPLETED
            step.completed_at = datetime.now()
            step.result = result
            self._save_task(task)

    def fail_step(self, task: Task, step_index: int, error: str):
        """Fail a step"""
        if step_index < len(task.steps):
            step = task.steps[step_index]
            step.status = TaskStatus.FAILED
            step.completed_at = datetime.now()
            step.error = error
            self._save_task(task)

    def get_last_paused_task(self) -> Optional[Task]:
        """Get the most recently paused task"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT task_id FROM tasks
            WHERE status = ?
            ORDER BY paused_at DESC
            LIMIT 1
        """, (TaskStatus.PAUSED.value,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._load_task(row["task_id"])

        return None

    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT task_id FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
            """, (status.value,))
        else:
            cursor.execute("""
                SELECT task_id FROM tasks
                ORDER BY created_at DESC
            """)

        task_ids = [row["task_id"] for row in cursor.fetchall()]
        conn.close()

        return [self._load_task(tid) for tid in task_ids]

    def execute_with_checkpoints(self,
                                 description: str,
                                 steps: List[Dict[str, Any]],
                                 error_handler: Optional[Callable] = None) -> Any:
        """
        Execute a multi-step task with automatic checkpointing

        Args:
            description: Task description
            steps: List of steps, each with 'description' and 'func' (callable)
            error_handler: Optional error handler function

        Returns:
            Task result

        Example:
            steps = [
                {"description": "Load data", "func": load_data},
                {"description": "Process data", "func": process_data},
                {"description": "Save results", "func": save_results}
            ]
        """
        # Create task
        step_descriptions = [step["description"] for step in steps]
        task = self.create_task(description, step_descriptions)
        self.start_task(task)

        try:
            results = []

            for i, step_config in enumerate(steps):
                self.start_step(task, i)

                try:
                    # Execute step function
                    step_func = step_config["func"]
                    result = step_func()

                    # Complete step
                    self.complete_step(task, i, result)
                    results.append(result)

                except Exception as e:
                    # Handle step error
                    self.fail_step(task, i, str(e))

                    if error_handler:
                        error_handler(task, i, e)

                    raise

            # Complete task
            self.complete_task(task, results)
            return results

        except Exception as e:
            # Pause task on error (can resume later)
            self.pause_task(task)
            raise

    def _save_task(self, task: Task):
        """Save task to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Save task
        cursor.execute("""
            INSERT OR REPLACE INTO tasks
            (task_id, description, status, created_at, started_at, completed_at,
             paused_at, current_step_index, metadata, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.description,
            task.status.value,
            task.created_at.isoformat(),
            task.started_at.isoformat() if task.started_at else None,
            task.completed_at.isoformat() if task.completed_at else None,
            task.paused_at.isoformat() if task.paused_at else None,
            task.current_step_index,
            json.dumps(task.metadata),
            json.dumps(task.result) if task.result else None,
            task.error
        ))

        # Save steps
        for step in task.steps:
            cursor.execute("""
                INSERT OR REPLACE INTO task_steps
                (task_id, step_id, description, status, started_at, completed_at, result, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                step.step_id,
                step.description,
                step.status.value,
                step.started_at.isoformat() if step.started_at else None,
                step.completed_at.isoformat() if step.completed_at else None,
                json.dumps(step.result) if step.result else None,
                step.error
            ))

        conn.commit()
        conn.close()

    def _load_task(self, task_id: str) -> Optional[Task]:
        """Load task from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load task
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task_row = cursor.fetchone()

        if not task_row:
            conn.close()
            return None

        # Load steps
        cursor.execute("""
            SELECT * FROM task_steps
            WHERE task_id = ?
            ORDER BY step_id
        """, (task_id,))

        step_rows = cursor.fetchall()
        conn.close()

        # Construct task object
        task = Task(
            task_id=task_row["task_id"],
            description=task_row["description"],
            status=TaskStatus(task_row["status"]),
            created_at=datetime.fromisoformat(task_row["created_at"]),
            started_at=datetime.fromisoformat(task_row["started_at"]) if task_row["started_at"] else None,
            completed_at=datetime.fromisoformat(task_row["completed_at"]) if task_row["completed_at"] else None,
            paused_at=datetime.fromisoformat(task_row["paused_at"]) if task_row["paused_at"] else None,
            current_step_index=task_row["current_step_index"],
            metadata=json.loads(task_row["metadata"]) if task_row["metadata"] else {},
            result=json.loads(task_row["result"]) if task_row["result"] else None,
            error=task_row["error"]
        )

        # Add steps
        for step_row in step_rows:
            step = TaskStep(
                step_id=step_row["step_id"],
                description=step_row["description"],
                status=TaskStatus(step_row["status"]),
                started_at=datetime.fromisoformat(step_row["started_at"]) if step_row["started_at"] else None,
                completed_at=datetime.fromisoformat(step_row["completed_at"]) if step_row["completed_at"] else None,
                result=json.loads(step_row["result"]) if step_row["result"] else None,
                error=step_row["error"]
            )
            task.steps.append(step)

        return task

    def checkpoint(self):
        """Create a checkpoint of current task state"""
        if self.current_task:
            self._save_task(self.current_task)

class InterruptionHandler:
    """
    Handles graceful interruption (Ctrl+C) with state saving

    Usage:
        handler = InterruptionHandler(task_manager)
        handler.install_handler()

        # Now Ctrl+C will save state and exit gracefully
    """

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.interrupted = False

    def install_handler(self):
        """Install signal handler for SIGINT (Ctrl+C)"""
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal"""
        if self.interrupted:
            # Second Ctrl+C - force exit
            print("\n\nForce exit...")
            sys.exit(1)

        self.interrupted = True
        print("\n\n⏸️  Interrupt received. Saving state...")

        # Save current task state
        if self.task_manager.current_task:
            self.task_manager.pause_task(self.task_manager.current_task)
            print(f"✓ Task paused: {self.task_manager.current_task.description}")
            print(f"Resume with: ryx ::resume")
        else:
            print("No active task to save.")

        sys.exit(0)

    def check_interrupted(self):
        """Check if interrupted (for periodic checks in loops)"""
        return self.interrupted
