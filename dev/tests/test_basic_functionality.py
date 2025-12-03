#!/usr/bin/env python3
"""
Ryx AI - Basic Functionality Tests
Quick smoke tests to verify core features work
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all core modules can be imported"""
    print("Testing imports...")

    try:
        from core.ai_engine_v2 import AIEngineV2
        from core.model_orchestrator import ModelOrchestrator
        from core.meta_learner import MetaLearner
        from core.health_monitor import HealthMonitor
        from core.task_manager import TaskManager
        from core.rag_system import RAGSystem
    except ImportError as e:
        print(f"Import failed: {e}")
        raise

def reverse_string(s):
    """Reverse a given string."""
    return s[::-1]

def test_reverse_string():
    """Test the reverse_string function."""
    test_cases = [
        ("hello", "olleh"),
        ("world", "dlrow"),
        ("", ""),
        ("a", "a"),
        ("Python", "nohtyP")
    ]

    for input_str, expected_output in test_cases:
        assert reverse_string(input_str) == expected_output, f"Failed for input: {input_str}"

if __name__ == "__main__":
    test_imports()
    test_reverse_string()
    print("All tests passed.")