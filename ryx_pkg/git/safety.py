"""
Ryx Git Safety

Pre-commit validation and recovery mechanisms.
Ensures safe git operations for automated agents.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety level for git operations"""
    STRICT = "strict"    # Require clean state, confirm all
    NORMAL = "normal"    # Allow staged, confirm risky
    LOOSE = "loose"      # Allow dirty, minimal confirms


@dataclass
class SafetyCheck:
    """Result of a safety check"""
    passed: bool
    level: str
    message: str
    can_proceed: bool = True
    requires_confirm: bool = False


class GitSafety:
    """
    Git safety layer for Ryx.
    
    Provides:
    - Pre-operation checks
    - Automatic backups
    - Recovery mechanisms
    - Confirmation prompts for risky operations
    """
    
    # Patterns for files that should never be auto-committed
    PROTECTED_PATTERNS = [
        '.env', '.env.*', '*.key', '*.pem', '*.secret',
        'credentials*', 'secrets*', 'password*',
        '.git/*', '.gitignore'  # Let user handle these
    ]
    
    # Patterns for large files to warn about
    LARGE_FILE_THRESHOLD = 1024 * 1024  # 1MB
    
    def __init__(
        self,
        git_manager,
        safety_level: SafetyLevel = SafetyLevel.NORMAL,
        confirm_callback: Callable[[str], bool] = None
    ):
        """
        Initialize GitSafety.
        
        Args:
            git_manager: GitManager instance
            safety_level: Default safety level
            confirm_callback: Function to confirm risky operations
        """
        self.git = git_manager
        self.safety_level = safety_level
        self.confirm_callback = confirm_callback or (lambda msg: False)
        
        self._backup_commits = []  # Track commits we've made for rollback
    
    def check_pre_commit(self, files: List[str] = None) -> SafetyCheck:
        """
        Run pre-commit safety checks.
        
        Args:
            files: Files to be committed
            
        Returns:
            SafetyCheck result
        """
        if not self.git.is_repo:
            return SafetyCheck(
                passed=False,
                level="error",
                message="Not in a git repository",
                can_proceed=False
            )
        
        status = self.git.get_status()
        
        # Check for protected files
        files_to_check = files or status.staged + status.modified
        protected = self._find_protected_files(files_to_check)
        
        if protected:
            return SafetyCheck(
                passed=False,
                level="warning",
                message=f"Protected files detected: {', '.join(protected)}",
                requires_confirm=True
            )
        
        # Check for large files
        large_files = self._find_large_files(files_to_check)
        if large_files:
            return SafetyCheck(
                passed=True,
                level="warning",
                message=f"Large files detected: {', '.join(large_files)}",
                requires_confirm=self.safety_level == SafetyLevel.STRICT
            )
        
        # Check repository state based on safety level
        if self.safety_level == SafetyLevel.STRICT:
            if status.modified or status.untracked:
                return SafetyCheck(
                    passed=False,
                    level="warning",
                    message="Repository has uncommitted changes",
                    requires_confirm=True
                )
        
        return SafetyCheck(
            passed=True,
            level="ok",
            message="All safety checks passed"
        )
    
    def _find_protected_files(self, files: List[str]) -> List[str]:
        """Find files matching protected patterns"""
        import fnmatch
        
        protected = []
        for f in files:
            for pattern in self.PROTECTED_PATTERNS:
                if fnmatch.fnmatch(f.lower(), pattern.lower()):
                    protected.append(f)
                    break
        return protected
    
    def _find_large_files(self, files: List[str]) -> List[str]:
        """Find files exceeding size threshold"""
        if not self.git.root:
            return []
        
        large = []
        for f in files:
            path = Path(self.git.root) / f
            try:
                if path.exists() and path.stat().st_size > self.LARGE_FILE_THRESHOLD:
                    large.append(f)
            except OSError:
                pass
        return large
    
    def safe_commit(
        self,
        message: str,
        files: List[str] = None,
        check_safety: bool = True
    ) -> Optional[str]:
        """
        Commit with safety checks.
        
        Args:
            message: Commit message
            files: Files to commit
            check_safety: Run safety checks
            
        Returns:
            Commit hash if successful
        """
        if check_safety:
            check = self.check_pre_commit(files)
            
            if not check.passed:
                if check.requires_confirm:
                    if not self.confirm_callback(
                        f"Safety warning: {check.message}\nProceed anyway?"
                    ):
                        logger.info("Commit cancelled by user")
                        return None
                elif not check.can_proceed:
                    logger.warning(f"Commit blocked: {check.message}")
                    return None
        
        commit_hash = self.git.safe_commit(message, files)
        
        if commit_hash:
            self._backup_commits.append(commit_hash)
        
        return commit_hash
    
    def create_backup_point(self, message: str = "Ryx backup") -> Optional[str]:
        """
        Create a backup commit before major changes.
        
        Args:
            message: Backup commit message
            
        Returns:
            Commit hash if created
        """
        status = self.git.get_status()
        
        if status.dirty:
            # Commit current state as backup
            commit = self.git.commit(f"backup: {message}", add_author_suffix=True)
            if commit:
                self._backup_commits.append(commit)
            return commit
        
        # No changes to backup
        return self.git.get_status().last_commit
    
    def rollback_to_backup(self, backup_commit: str = None) -> bool:
        """
        Rollback to a backup point.
        
        Args:
            backup_commit: Specific backup to rollback to
            
        Returns:
            True if successful
        """
        if backup_commit:
            return self.git.checkout(backup_commit)
        
        if self._backup_commits:
            # Rollback to most recent backup
            return self.git.undo(len(self._backup_commits))
        
        return False
    
    def with_backup(self, operation: Callable[[], bool]) -> bool:
        """
        Execute an operation with automatic backup.
        
        Creates a backup before the operation and rolls back on failure.
        
        Args:
            operation: Function to execute
            
        Returns:
            True if operation succeeded
        """
        backup = self.create_backup_point("pre-operation")
        
        try:
            result = operation()
            if result:
                return True
            
            # Operation failed, rollback
            logger.warning("Operation failed, rolling back")
            self.rollback_to_backup(backup)
            return False
            
        except Exception as e:
            logger.error(f"Operation error: {e}, rolling back")
            self.rollback_to_backup(backup)
            raise
