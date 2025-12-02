"""
Ryx AI - Checkpoint System

Provides undo/rollback functionality for all file operations.
Like git but for individual operations within a session.

Features:
- Automatic checkpoint before any file modification
- Named checkpoints for major operations
- Undo last N changes
- Rollback to specific checkpoint
- Git integration (auto-commit option)
"""

import os
import shutil
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.paths import get_data_dir


class ChangeType(Enum):
    """Types of file changes"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileChange:
    """Record of a single file change"""
    path: str
    change_type: ChangeType
    old_content: Optional[str] = None  # For MODIFY/DELETE
    new_content: Optional[str] = None  # For CREATE/MODIFY
    old_path: Optional[str] = None     # For RENAME
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'change_type': self.change_type.value,
            'old_content': self.old_content,
            'new_content': self.new_content,
            'old_path': self.old_path,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'FileChange':
        return cls(
            path=d['path'],
            change_type=ChangeType(d['change_type']),
            old_content=d.get('old_content'),
            new_content=d.get('new_content'),
            old_path=d.get('old_path'),
            timestamp=d.get('timestamp', datetime.now().isoformat())
        )


@dataclass
class Checkpoint:
    """A named checkpoint with multiple file changes"""
    id: str
    name: str
    description: str
    changes: List[FileChange] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    task_context: Optional[str] = None  # What task created this
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'changes': [c.to_dict() for c in self.changes],
            'timestamp': self.timestamp,
            'task_context': self.task_context
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Checkpoint':
        return cls(
            id=d['id'],
            name=d['name'],
            description=d['description'],
            changes=[FileChange.from_dict(c) for c in d.get('changes', [])],
            timestamp=d.get('timestamp', datetime.now().isoformat()),
            task_context=d.get('task_context')
        )


class CheckpointManager:
    """
    Manages checkpoints for undo/rollback functionality.
    
    Usage:
        cp = CheckpointManager()
        
        # Before making changes
        cp.start_checkpoint("create_login", "Creating login function")
        
        # Track each change
        cp.track_create("/path/to/new/file.py", content)
        cp.track_modify("/path/to/existing.py", old_content, new_content)
        
        # Commit checkpoint
        cp.commit_checkpoint()
        
        # Undo last checkpoint
        cp.undo()
        
        # Rollback to specific checkpoint
        cp.rollback("create_login")
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.checkpoints_dir = get_data_dir() / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.checkpoints_dir / f"session_{self.session_id}.json"
        
        self.checkpoints: List[Checkpoint] = []
        self.current_checkpoint: Optional[Checkpoint] = None
        self._pending_changes: List[FileChange] = []
        
        self._load_session()
    
    def _load_session(self):
        """Load checkpoints from current session"""
        if self.session_file.exists():
            try:
                with open(self.session_file) as f:
                    data = json.load(f)
                self.checkpoints = [Checkpoint.from_dict(cp) for cp in data.get('checkpoints', [])]
            except Exception:
                self.checkpoints = []
    
    def _save_session(self):
        """Save checkpoints to disk"""
        data = {
            'session_id': self.session_id,
            'checkpoints': [cp.to_dict() for cp in self.checkpoints],
            'last_updated': datetime.now().isoformat()
        }
        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_id(self, name: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = datetime.now().strftime("%H%M%S")
        hash_part = hashlib.md5(f"{name}{timestamp}".encode()).hexdigest()[:6]
        return f"{name}_{hash_part}"
    
    # ─────────────────────────────────────────────────────────────────────────
    # Checkpoint Creation
    # ─────────────────────────────────────────────────────────────────────────
    
    def start_checkpoint(self, name: str, description: str = "", task_context: str = "") -> str:
        """
        Start a new checkpoint. All tracked changes will be grouped under this.
        
        Returns checkpoint ID.
        """
        cp_id = self._generate_id(name)
        self.current_checkpoint = Checkpoint(
            id=cp_id,
            name=name,
            description=description,
            task_context=task_context
        )
        self._pending_changes = []
        return cp_id
    
    def track_create(self, path: str, content: str):
        """Track a file creation"""
        change = FileChange(
            path=str(path),
            change_type=ChangeType.CREATE,
            new_content=content
        )
        self._pending_changes.append(change)
    
    def track_modify(self, path: str, old_content: str, new_content: str):
        """Track a file modification"""
        change = FileChange(
            path=str(path),
            change_type=ChangeType.MODIFY,
            old_content=old_content,
            new_content=new_content
        )
        self._pending_changes.append(change)
    
    def track_delete(self, path: str, old_content: str):
        """Track a file deletion"""
        change = FileChange(
            path=str(path),
            change_type=ChangeType.DELETE,
            old_content=old_content
        )
        self._pending_changes.append(change)
    
    def track_rename(self, old_path: str, new_path: str, content: str):
        """Track a file rename"""
        change = FileChange(
            path=str(new_path),
            change_type=ChangeType.RENAME,
            old_path=str(old_path),
            old_content=content,
            new_content=content
        )
        self._pending_changes.append(change)
    
    def commit_checkpoint(self, git_commit: bool = False) -> Optional[Checkpoint]:
        """
        Commit the current checkpoint with all tracked changes.
        
        Args:
            git_commit: If True, also create a git commit
            
        Returns the committed checkpoint.
        """
        if not self.current_checkpoint:
            return None
        
        if not self._pending_changes:
            # No changes, discard checkpoint
            self.current_checkpoint = None
            return None
        
        # Add changes to checkpoint
        self.current_checkpoint.changes = self._pending_changes.copy()
        
        # Store
        self.checkpoints.append(self.current_checkpoint)
        self._save_session()
        
        committed = self.current_checkpoint
        
        # Optional git commit
        if git_commit:
            self._git_commit(committed)
        
        # Reset state
        self.current_checkpoint = None
        self._pending_changes = []
        
        return committed
    
    def discard_checkpoint(self):
        """Discard the current checkpoint without saving"""
        self.current_checkpoint = None
        self._pending_changes = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # Quick Tracking (Auto checkpoint)
    # ─────────────────────────────────────────────────────────────────────────
    
    def quick_track(self, name: str, path: str, change_type: ChangeType, 
                    old_content: Optional[str] = None, new_content: Optional[str] = None) -> Checkpoint:
        """
        Quick track a single change with auto-checkpoint.
        
        Useful for simple operations that don't need explicit start/commit.
        """
        self.start_checkpoint(name, f"Quick: {change_type.value} {path}")
        
        if change_type == ChangeType.CREATE:
            self.track_create(path, new_content or "")
        elif change_type == ChangeType.MODIFY:
            self.track_modify(path, old_content or "", new_content or "")
        elif change_type == ChangeType.DELETE:
            self.track_delete(path, old_content or "")
        
        return self.commit_checkpoint()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Undo / Rollback
    # ─────────────────────────────────────────────────────────────────────────
    
    def undo(self, count: int = 1) -> List[Tuple[str, bool, str]]:
        """
        Undo the last N checkpoints.
        
        Returns list of (checkpoint_name, success, message) tuples.
        """
        results = []
        
        for _ in range(min(count, len(self.checkpoints))):
            if not self.checkpoints:
                break
            
            cp = self.checkpoints.pop()
            success, msg = self._revert_checkpoint(cp)
            results.append((cp.name, success, msg))
        
        self._save_session()
        return results
    
    def rollback(self, checkpoint_id: str) -> Tuple[bool, str, int]:
        """
        Rollback to a specific checkpoint (undo everything after it).
        
        Returns (success, message, changes_reverted).
        """
        # Find checkpoint index
        idx = None
        for i, cp in enumerate(self.checkpoints):
            if cp.id == checkpoint_id or cp.name == checkpoint_id:
                idx = i
                break
        
        if idx is None:
            return False, f"Checkpoint not found: {checkpoint_id}", 0
        
        # Undo all checkpoints after this one (in reverse order)
        changes_reverted = 0
        errors = []
        
        while len(self.checkpoints) > idx + 1:
            cp = self.checkpoints.pop()
            success, msg = self._revert_checkpoint(cp)
            if success:
                changes_reverted += len(cp.changes)
            else:
                errors.append(msg)
        
        self._save_session()
        
        if errors:
            return False, f"Partial rollback. Errors: {'; '.join(errors)}", changes_reverted
        
        return True, f"Rolled back to '{checkpoint_id}'", changes_reverted
    
    def _revert_checkpoint(self, cp: Checkpoint) -> Tuple[bool, str]:
        """Revert all changes in a checkpoint (in reverse order)"""
        errors = []
        
        for change in reversed(cp.changes):
            try:
                if change.change_type == ChangeType.CREATE:
                    # Delete the created file
                    path = Path(change.path)
                    if path.exists():
                        path.unlink()
                
                elif change.change_type == ChangeType.MODIFY:
                    # Restore old content
                    path = Path(change.path)
                    if change.old_content is not None:
                        path.write_text(change.old_content)
                
                elif change.change_type == ChangeType.DELETE:
                    # Restore deleted file
                    path = Path(change.path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if change.old_content is not None:
                        path.write_text(change.old_content)
                
                elif change.change_type == ChangeType.RENAME:
                    # Rename back
                    new_path = Path(change.path)
                    old_path = Path(change.old_path)
                    if new_path.exists():
                        new_path.rename(old_path)
                        
            except Exception as e:
                errors.append(f"{change.path}: {e}")
        
        if errors:
            return False, f"Errors reverting {cp.name}: {'; '.join(errors)}"
        
        return True, f"Reverted {len(cp.changes)} changes from '{cp.name}'"
    
    # ─────────────────────────────────────────────────────────────────────────
    # List / Status
    # ─────────────────────────────────────────────────────────────────────────
    
    def list_checkpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent checkpoints"""
        result = []
        for cp in self.checkpoints[-limit:]:
            result.append({
                'id': cp.id,
                'name': cp.name,
                'description': cp.description,
                'changes': len(cp.changes),
                'timestamp': cp.timestamp,
                'files': [c.path for c in cp.changes[:5]]
            })
        return list(reversed(result))
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a specific checkpoint by ID or name"""
        for cp in self.checkpoints:
            if cp.id == checkpoint_id or cp.name == checkpoint_id:
                return cp
        return None
    
    def has_checkpoints(self) -> bool:
        """Check if there are any checkpoints to undo"""
        return len(self.checkpoints) > 0
    
    def last_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint"""
        return self.checkpoints[-1] if self.checkpoints else None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Git Integration
    # ─────────────────────────────────────────────────────────────────────────
    
    def _git_commit(self, cp: Checkpoint):
        """Create a git commit for a checkpoint"""
        try:
            # Stage changed files
            for change in cp.changes:
                if change.change_type == ChangeType.DELETE:
                    subprocess.run(['git', 'rm', '--quiet', change.path], 
                                   capture_output=True, check=False)
                else:
                    subprocess.run(['git', 'add', change.path], 
                                   capture_output=True, check=False)
            
            # Commit
            message = f"[ryx] {cp.name}: {cp.description or 'Auto-checkpoint'}"
            subprocess.run(['git', 'commit', '-m', message, '--quiet'],
                          capture_output=True, check=False)
        except Exception:
            pass  # Git errors are non-fatal
    
    def git_undo_last(self) -> Tuple[bool, str]:
        """Undo the last git commit (soft reset)"""
        try:
            result = subprocess.run(
                ['git', 'reset', '--soft', 'HEAD~1'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True, "Git commit undone (soft reset)"
            return False, result.stderr
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════════════════════

_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create global checkpoint manager"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════════

def checkpoint(name: str, description: str = "") -> str:
    """Start a new checkpoint (convenience function)"""
    return get_checkpoint_manager().start_checkpoint(name, description)


def undo(count: int = 1) -> List[Tuple[str, bool, str]]:
    """Undo last N checkpoints (convenience function)"""
    return get_checkpoint_manager().undo(count)


def rollback(checkpoint_id: str) -> Tuple[bool, str, int]:
    """Rollback to checkpoint (convenience function)"""
    return get_checkpoint_manager().rollback(checkpoint_id)


def list_checkpoints(limit: int = 10) -> List[Dict[str, Any]]:
    """List recent checkpoints (convenience function)"""
    return get_checkpoint_manager().list_checkpoints(limit)
