"""
Ryx Testing Module

Provides test discovery and execution for verification.
Supports multiple test frameworks.

Key Components:
- TestRunner: Execute tests and parse results
- TestDetector: Auto-detect test framework
- TestResult: Structured test results

Usage:
    from ryx_pkg.testing import TestRunner, detect_framework
    
    runner = TestRunner("/path/to/project")
    results = runner.run()
"""

from .test_runner import TestRunner, TestResult, TestStatus
from .detector import TestDetector, detect_framework

__all__ = [
    'TestRunner',
    'TestResult',
    'TestStatus',
    'TestDetector',
    'detect_framework',
]
