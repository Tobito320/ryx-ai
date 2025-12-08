"""
Ryx AI - TODO Task Manager (Inspired by Claude Code)

When Ryx receives a complex request like "resume work on ryxsurf",
it should:
1. Explore the codebase to understand current state
2. Create a TODO list of tasks
3. Work through tasks one by one
4. Update progress as it goes

This makes Ryx autonomous and able to handle vague prompts.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path
from datetime import datetime


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """A single task in the TODO list"""
    id: str
    content: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10, higher = more important
    context: Optional[str] = None  # Related files, notes
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority,
            "context": self.context,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            id=data["id"],
            content=data["content"],
            status=TaskStatus(data["status"]),
            priority=data.get("priority", 5),
            context=data.get("context"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at")
        )


class TodoManager:
    """
    Manages a TODO list for the current session.
    
    Key behaviors (from Claude Code):
    - Only ONE task in_progress at a time
    - Mark complete IMMEDIATELY after finishing
    - Break complex tasks into smaller steps
    - Track blocking issues
    """
    
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.tasks: List[Task] = []
        self.session_file = self.project_dir / "data" / "current_session.json"
        self._load_session()
    
    def _load_session(self):
        """Load tasks from current session file"""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text())
                self.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
            except:
                self.tasks = []
    
    def _save_session(self):
        """Save tasks to session file"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"tasks": [t.to_dict() for t in self.tasks]}
        self.session_file.write_text(json.dumps(data, indent=2))
    
    def add_task(self, content: str, priority: int = 5, context: str = None) -> Task:
        """Add a new task"""
        task_id = f"task_{len(self.tasks) + 1}_{datetime.now().strftime('%H%M%S')}"
        task = Task(
            id=task_id,
            content=content,
            priority=priority,
            context=context
        )
        self.tasks.append(task)
        self._save_session()
        return task
    
    def add_tasks(self, task_list: List[str]) -> List[Task]:
        """Add multiple tasks at once"""
        added = []
        for i, content in enumerate(task_list):
            task = self.add_task(content, priority=10 - i)  # Earlier = higher priority
            added.append(task)
        return added
    
    def start_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as in_progress (only ONE at a time)"""
        # First, ensure no other task is in_progress
        for task in self.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.PENDING
        
        # Start the requested task
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.IN_PROGRESS
                self._save_session()
                return task
        return None
    
    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                self._save_session()
                return task
        return None
    
    def block_task(self, task_id: str, reason: str) -> Optional[Task]:
        """Mark a task as blocked with reason"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.BLOCKED
                task.context = f"BLOCKED: {reason}"
                self._save_session()
                return task
        return None
    
    def get_next_task(self) -> Optional[Task]:
        """Get the highest priority pending task"""
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        if not pending:
            return None
        return max(pending, key=lambda t: t.priority)
    
    def get_current_task(self) -> Optional[Task]:
        """Get the currently in_progress task"""
        for task in self.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None
    
    def get_status_summary(self) -> str:
        """Get a summary of all tasks"""
        if not self.tasks:
            return "No tasks in TODO list"
        
        lines = ["📋 TODO List:"]
        
        # Group by status
        current = [t for t in self.tasks if t.status == TaskStatus.IN_PROGRESS]
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        completed = [t for t in self.tasks if t.status == TaskStatus.COMPLETED]
        blocked = [t for t in self.tasks if t.status == TaskStatus.BLOCKED]
        
        if current:
            lines.append("\n🔄 IN PROGRESS:")
            for t in current:
                lines.append(f"  → {t.content}")
        
        if pending:
            lines.append("\n⏳ PENDING:")
            for t in sorted(pending, key=lambda x: -x.priority):
                lines.append(f"  ○ {t.content}")
        
        if blocked:
            lines.append("\n🚫 BLOCKED:")
            for t in blocked:
                lines.append(f"  ✗ {t.content}")
                if t.context:
                    lines.append(f"    {t.context}")
        
        if completed:
            lines.append(f"\n✅ COMPLETED: {len(completed)} tasks")
        
        return "\n".join(lines)
    
    def clear_completed(self):
        """Remove completed tasks from list"""
        self.tasks = [t for t in self.tasks if t.status != TaskStatus.COMPLETED]
        self._save_session()
    
    def reset(self):
        """Clear all tasks"""
        self.tasks = []
        self._save_session()


# Tool schema for LLM
TODO_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "todo_manager",
        "description": """Manage a TODO list for complex tasks. Use this when:
- Task has 3+ steps
- User gives vague request like "continue working on X"
- Multiple files need to be changed
- You need to track progress

Actions: add, start, complete, block, status, next""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "add_many", "start", "complete", "block", "status", "next", "reset"],
                    "description": "Action to perform"
                },
                "task_content": {
                    "type": "string",
                    "description": "Content for new task (for 'add' action)"
                },
                "task_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tasks (for 'add_many' action)"
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for start/complete/block)"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for blocking (for 'block' action)"
                }
            },
            "required": ["action"]
        }
    }
}
