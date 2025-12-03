"""
Ryx Git Integration Module

Provides Git operations with safety features for Ryx agents.
Inspired by Aider's git handling, adapted for Ryx's architecture.

Key Components:
- GitManager: Core Git operations with safety checks
- GitSafety: Pre-commit validation and recovery
- CommitHelper: Intelligent commit message generation

Usage:
    from ryx_pkg.git import GitManager
    
    git = GitManager("/path/to/repo")
    if git.is_repo:
        git.safe_commit("feat: add login button")
"""

from .git_manager import GitManager, GitStatus
from .safety import GitSafety, SafetyCheck
from .commit_helper import CommitHelper

__all__ = [
    'GitManager',
    'GitStatus',
    'GitSafety',
    'SafetyCheck',
    'CommitHelper',
]
