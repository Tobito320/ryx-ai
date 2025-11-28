"""
Ryx AI - Path Management
Auto-detects project root and provides consistent paths across all modules
"""

import os
from pathlib import Path


def get_project_root() -> Path:
    """
    Get project root directory

    Priority:
    1. RYX_PROJECT_ROOT environment variable (set by main executable)
    2. Detect from current file location
    3. Fallback to ~/ryx-ai

    Returns:
        Path to project root
    """
    # Check environment variable first
    if 'RYX_PROJECT_ROOT' in os.environ:
        return Path(os.environ['RYX_PROJECT_ROOT'])

    # Try to detect from this file's location
    # This file is at: <project_root>/core/paths.py
    current_file = Path(__file__).resolve()
    if current_file.parent.name == 'core':
        project_root = current_file.parent.parent
        if (project_root / 'core').exists() and (project_root / 'modes').exists():
            return project_root

    # Fallback to home directory
    return Path.home() / "ryx-ai"


def get_data_dir() -> Path:
    """Get data directory"""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o777)
    # Ensure directory is writable by all users
    try:
        data_dir.chmod(0o777)
    except (PermissionError, OSError):
        pass  # Best effort, may fail in restricted environments
    return data_dir


def get_config_dir() -> Path:
    """Get config directory"""
    config_dir = get_project_root() / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_log_dir() -> Path:
    """Get log directory"""
    log_dir = get_project_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o777)
    # Ensure directory is writable by all users
    try:
        log_dir.chmod(0o777)
    except (PermissionError, OSError):
        pass  # Best effort, may fail in restricted environments
    return log_dir


def get_cache_dir() -> Path:
    """Get cache directory"""
    cache_dir = Path.home() / ".cache" / "ryx-ai"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_runtime_dir() -> Path:
    """Get runtime directory for session state, etc."""
    runtime_dir = Path.home() / ".ryx"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir
