"""
Ryx Git Manager

Core Git operations with safety features for Ryx.
Provides automatic commits, diffs, status checks, and undo functionality.

Inspired by Aider's repo.py, adapted for Ryx architecture.
Original: https://github.com/paul-gauthier/aider (Apache 2.0 License)
"""

import os
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Current Git repository status"""
    is_repo: bool = False
    branch: str = ""
    dirty: bool = False
    staged: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""
    last_commit_msg: str = ""


class GitManager:
    """
    Git operations manager for Ryx.
    
    Provides:
    - Status checks and diff generation
    - Safe commits with validation
    - Undo/revert operations
    - Branch management
    - Stash operations
    
    Designed for safe, automated git operations by Ryx agents.
    """
    
    def __init__(self, root: str = None, author_suffix: str = "(ryx)"):
        """
        Initialize GitManager.
        
        Args:
            root: Repository root (defaults to cwd, searches parent dirs)
            author_suffix: Suffix to add to commit author name
        """
        self.root = self._find_repo_root(root or os.getcwd())
        self.author_suffix = author_suffix
        self._git_available = shutil.which('git') is not None
        
        if self.root:
            self.root = Path(self.root).resolve()
    
    def _find_repo_root(self, start: str) -> Optional[str]:
        """Find the git repository root"""
        path = Path(start).resolve()
        
        while path != path.parent:
            if (path / '.git').exists():
                return str(path)
            path = path.parent
        
        # Check if start itself is a repo
        if (Path(start) / '.git').exists():
            return start
        
        return None
    
    def _run_git(
        self,
        *args,
        check: bool = True,
        capture: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run a git command.
        
        Args:
            *args: Git command arguments
            check: Raise exception on non-zero exit
            capture: Capture stdout/stderr
            
        Returns:
            (return_code, stdout, stderr)
        """
        if not self._git_available:
            raise RuntimeError("Git is not available")
        
        if not self.root:
            raise RuntimeError("Not in a git repository")
        
        cmd = ['git'] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.root),
                capture_output=capture,
                text=True,
                timeout=30
            )
            
            if check and result.returncode != 0:
                logger.warning(f"Git command failed: {' '.join(cmd)}")
                logger.warning(f"stderr: {result.stderr}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"Git error: {e}")
            return -1, "", str(e)
    
    @property
    def is_repo(self) -> bool:
        """Check if we're in a git repository"""
        return self.root is not None and self._git_available
    
    def get_status(self) -> GitStatus:
        """
        Get current repository status.
        
        Returns:
            GitStatus with current state
        """
        status = GitStatus()
        
        if not self.is_repo:
            return status
        
        status.is_repo = True
        
        # Get branch
        code, stdout, _ = self._run_git('branch', '--show-current', check=False)
        if code == 0:
            status.branch = stdout.strip()
        
        # Get status
        code, stdout, _ = self._run_git('status', '--porcelain', check=False)
        if code == 0:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                
                indicator = line[:2]
                filepath = line[3:]
                
                if indicator[0] in ('M', 'A', 'D', 'R'):
                    status.staged.append(filepath)
                if indicator[1] == 'M':
                    status.modified.append(filepath)
                if indicator == '??':
                    status.untracked.append(filepath)
            
            status.dirty = bool(status.staged or status.modified or status.untracked)
        
        # Get last commit
        code, stdout, _ = self._run_git('log', '-1', '--format=%h', check=False)
        if code == 0:
            status.last_commit = stdout.strip()
        
        code, stdout, _ = self._run_git('log', '-1', '--format=%s', check=False)
        if code == 0:
            status.last_commit_msg = stdout.strip()[:50]
        
        # Get ahead/behind
        code, stdout, _ = self._run_git(
            'rev-list', '--left-right', '--count',
            f'{status.branch}...origin/{status.branch}',
            check=False
        )
        if code == 0:
            parts = stdout.strip().split('\t')
            if len(parts) == 2:
                status.ahead = int(parts[0])
                status.behind = int(parts[1])
        
        return status
    
    def get_diff(
        self,
        files: List[str] = None,
        staged: bool = False,
        context_lines: int = 3
    ) -> str:
        """
        Get diff of changes.
        
        Args:
            files: Specific files to diff (or all if None)
            staged: Get staged changes only
            context_lines: Lines of context
            
        Returns:
            Unified diff string
        """
        if not self.is_repo:
            return ""
        
        args = ['diff', f'-U{context_lines}']
        
        if staged:
            args.append('--staged')
        
        if files:
            args.append('--')
            args.extend(files)
        
        code, stdout, _ = self._run_git(*args, check=False)
        return stdout if code == 0 else ""
    
    def get_file_diff(self, filepath: str, staged: bool = False) -> str:
        """Get diff for a specific file"""
        return self.get_diff([filepath], staged=staged)
    
    def add(self, files: List[str] = None) -> bool:
        """
        Stage files for commit.
        
        Args:
            files: Files to add (or all if None)
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        if files:
            code, _, _ = self._run_git('add', '--', *files, check=False)
        else:
            code, _, _ = self._run_git('add', '-A', check=False)
        
        return code == 0
    
    def commit(
        self,
        message: str,
        files: List[str] = None,
        add_author_suffix: bool = True
    ) -> Optional[str]:
        """
        Create a commit.
        
        Args:
            message: Commit message
            files: Specific files to commit (or all staged if None)
            add_author_suffix: Add Ryx suffix to author name
            
        Returns:
            Commit hash if successful, None otherwise
        """
        if not self.is_repo:
            return None
        
        # Stage files if specified
        if files:
            if not self.add(files):
                return None
        
        # Build commit command
        args = ['commit', '-m', message]
        
        # Add author suffix if enabled
        if add_author_suffix:
            code, stdout, _ = self._run_git('config', 'user.name', check=False)
            if code == 0:
                author = stdout.strip()
                if not author.endswith(self.author_suffix):
                    author = f"{author} {self.author_suffix}"
                    args.extend(['--author', f'{author} <ryx@local>'])
        
        code, stdout, stderr = self._run_git(*args, check=False)
        
        if code == 0:
            # Get the new commit hash
            code, stdout, _ = self._run_git('rev-parse', '--short', 'HEAD', check=False)
            if code == 0:
                commit_hash = stdout.strip()
                logger.info(f"Committed: {commit_hash} - {message[:50]}")
                return commit_hash
        
        logger.warning(f"Commit failed: {stderr}")
        return None
    
    def safe_commit(
        self,
        message: str,
        files: List[str] = None,
        prefix: str = "ryx: "
    ) -> Optional[str]:
        """
        Safe commit with automatic staging and message formatting.
        
        Args:
            message: Commit message (prefix will be added)
            files: Specific files to commit
            prefix: Message prefix
            
        Returns:
            Commit hash if successful
        """
        if not self.is_repo:
            logger.warning("Not in a git repository")
            return None
        
        status = self.get_status()
        
        # Check if there's anything to commit
        if files:
            has_changes = any(f in status.modified or f in status.untracked for f in files)
        else:
            has_changes = status.dirty
        
        if not has_changes:
            logger.info("Nothing to commit")
            return None
        
        # Add prefix to message
        if not message.startswith(prefix):
            message = prefix + message
        
        return self.commit(message, files)
    
    def undo(self, num_commits: int = 1) -> bool:
        """
        Undo recent commits.
        
        Args:
            num_commits: Number of commits to undo
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        code, _, stderr = self._run_git(
            'reset', '--soft', f'HEAD~{num_commits}',
            check=False
        )
        
        if code == 0:
            logger.info(f"Undid {num_commits} commit(s)")
            return True
        
        logger.warning(f"Undo failed: {stderr}")
        return False
    
    def revert(self, commit_hash: str) -> bool:
        """
        Revert a specific commit.
        
        Args:
            commit_hash: Commit to revert
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        code, _, stderr = self._run_git(
            'revert', '--no-commit', commit_hash,
            check=False
        )
        
        if code == 0:
            logger.info(f"Reverted commit: {commit_hash}")
            return True
        
        logger.warning(f"Revert failed: {stderr}")
        return False
    
    def stash(self, message: str = None) -> bool:
        """
        Stash current changes.
        
        Args:
            message: Optional stash message
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        args = ['stash', 'push']
        if message:
            args.extend(['-m', message])
        
        code, _, _ = self._run_git(*args, check=False)
        return code == 0
    
    def stash_pop(self) -> bool:
        """Pop the most recent stash"""
        if not self.is_repo:
            return False
        
        code, _, _ = self._run_git('stash', 'pop', check=False)
        return code == 0
    
    def create_branch(self, name: str, checkout: bool = True) -> bool:
        """
        Create a new branch.
        
        Args:
            name: Branch name
            checkout: Switch to the new branch
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        if checkout:
            code, _, _ = self._run_git('checkout', '-b', name, check=False)
        else:
            code, _, _ = self._run_git('branch', name, check=False)
        
        return code == 0
    
    def checkout(self, ref: str) -> bool:
        """
        Checkout a branch or commit.
        
        Args:
            ref: Branch name or commit hash
            
        Returns:
            True if successful
        """
        if not self.is_repo:
            return False
        
        code, _, _ = self._run_git('checkout', ref, check=False)
        return code == 0
    
    def get_commits(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent commits.
        
        Args:
            limit: Maximum number of commits
            
        Returns:
            List of commit dicts with hash, message, author, date
        """
        if not self.is_repo:
            return []
        
        code, stdout, _ = self._run_git(
            'log', f'-{limit}',
            '--format=%H|%s|%an|%ai',
            check=False
        )
        
        if code != 0:
            return []
        
        commits = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|', 3)
            if len(parts) >= 4:
                commits.append({
                    'hash': parts[0][:8],
                    'message': parts[1][:80],
                    'author': parts[2],
                    'date': parts[3]
                })
        
        return commits
    
    def get_changed_files(self, since_commit: str = None) -> List[str]:
        """
        Get files changed since a commit.
        
        Args:
            since_commit: Compare against this commit (default: HEAD~1)
            
        Returns:
            List of changed file paths
        """
        if not self.is_repo:
            return []
        
        ref = since_commit or 'HEAD~1'
        
        code, stdout, _ = self._run_git(
            'diff', '--name-only', ref,
            check=False
        )
        
        if code == 0:
            return [f for f in stdout.strip().split('\n') if f]
        
        return []
    
    def ensure_clean(self, stash_if_dirty: bool = False) -> bool:
        """
        Ensure the repository is in a clean state.
        
        Args:
            stash_if_dirty: Stash changes if dirty
            
        Returns:
            True if clean (or stashed successfully)
        """
        status = self.get_status()
        
        if not status.dirty:
            return True
        
        if stash_if_dirty:
            return self.stash("Ryx auto-stash")
        
        return False
    
    def format_status(self) -> str:
        """Get a formatted status string for display"""
        status = self.get_status()
        
        if not status.is_repo:
            return "Not a git repository"
        
        lines = []
        lines.append(f"Branch: {status.branch or 'detached'}")
        
        if status.last_commit:
            lines.append(f"Last commit: {status.last_commit} - {status.last_commit_msg}")
        
        if status.ahead or status.behind:
            lines.append(f"↑{status.ahead} ↓{status.behind}")
        
        if status.dirty:
            if status.staged:
                lines.append(f"Staged: {len(status.staged)} file(s)")
            if status.modified:
                lines.append(f"Modified: {len(status.modified)} file(s)")
            if status.untracked:
                lines.append(f"Untracked: {len(status.untracked)} file(s)")
        else:
            lines.append("Clean")
        
        return '\n'.join(lines)
