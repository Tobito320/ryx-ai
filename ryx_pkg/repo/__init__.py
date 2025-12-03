"""
Ryx Repository Understanding Module

Provides automatic repository exploration and file selection.
Inspired by Aider's repomap system, adapted for Ryx's agent architecture.

Key Components:
- RepoMap: Builds a map of the repository with tags and definitions
- RepoExplorer: Scans and indexes repositories
- FileSelector: Finds relevant files for a given task

Usage:
    from ryx_pkg.repo import RepoMap, find_relevant_files
    
    repo_map = RepoMap(root="/path/to/project")
    files = repo_map.find_relevant_files("fix the login button")
"""

from .repo_map import RepoMap, Tag
from .file_selector import FileSelector, find_relevant_files
from .explorer import RepoExplorer

__all__ = [
    'RepoMap',
    'Tag', 
    'FileSelector',
    'find_relevant_files',
    'RepoExplorer',
]
