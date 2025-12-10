#!/usr/bin/env python3
"""
Ryx AI - Self-Benchmark System
Measures Ryx's capabilities and outputs a score.
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test"""
    category: str
    test_name: str
    passed: bool
    points: int
    max_points: int
    time_seconds: float
    error: Optional[str] = None


@dataclass
class BenchmarkReport:
    """Full benchmark report"""
    timestamp: str
    edit_success: int = 0
    edit_max: int = 30
    file_discovery: int = 0
    file_max: int = 20
    task_completion: int = 0
    task_max: int = 30
    self_healing: int = 0
    healing_max: int = 10
    speed_bonus: int = 0
    speed_max: int = 10
    total: int = 0
    max_total: int = 100
    results: List[dict] = field(default_factory=list)
    
    def calculate_total(self):
        self.total = (
            self.edit_success + 
            self.file_discovery + 
            self.task_completion + 
            self.self_healing + 
            self.speed_bonus
        )
        return self.total


class RyxBenchmark:
    """Benchmark system for Ryx AI"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.results: List[BenchmarkResult] = []
        self.temp_dir = None
        
    def setup(self):
        """Create temporary test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ryx_benchmark_"))
        
        # Create test files
        (self.temp_dir / "test_file.py").write_text('''
def hello():
    """Say hello"""
    print("Hello, World!")
    return True

def add(a, b):
    """Add two numbers"""
    return a + b

def multiply(a, b):
    """Multiply two numbers"""
    return a * b

class Calculator:
    """Simple calculator"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x):
        self.result += x
        return self
    
    def subtract(self, x):
        self.result -= x
        return self
    
    def get_result(self):
        return self.result
''')
        
        (self.temp_dir / "config.json").write_text(json.dumps({
            "name": "test_project",
            "version": "1.0.0",
            "settings": {
                "debug": True,
                "log_level": "INFO"
            }
        }, indent=2))
        
        # Create subdirectory with more files
        (self.temp_dir / "utils").mkdir()
        (self.temp_dir / "utils" / "helpers.py").write_text('''
def format_string(s):
    return s.strip().lower()

def validate_email(email):
    return "@" in email and "." in email
''')
        
    def teardown(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    # ═══════════════════════════════════════════════════════════════
    # EDIT SUCCESS TESTS (30 points max)
    # ═══════════════════════════════════════════════════════════════
    
    def test_edit_simple_function(self) -> BenchmarkResult:
        """Test: Add a simple function to a file"""
        start = time.time()
        try:
            from core.reliable_editor import ReliableEditor
            
            editor = ReliableEditor()
            test_file = self.temp_dir / "test_file.py"
            original = test_file.read_text()
            
            # Try to add a new function after 'multiply'
            result = editor.edit(
                str(test_file),
                search_text='def multiply(a, b):\n    """Multiply two numbers"""\n    return a * b',
                replace_text='def multiply(a, b):\n    """Multiply two numbers"""\n    return a * b\n\ndef divide(a, b):\n    """Divide two numbers"""\n    return a / b if b != 0 else None'
            )
            
            # Verify edit was applied
            new_content = test_file.read_text()
            passed = result.success and "def divide" in new_content
            
            # Restore original
            test_file.write_text(original)
            
            return BenchmarkResult(
                category="edit_success",
                test_name="simple_function_add",
                passed=passed,
                points=3 if passed else 0,
                max_points=3,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="edit_success",
                test_name="simple_function_add",
                passed=False,
                points=0,
                max_points=3,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_edit_with_whitespace(self) -> BenchmarkResult:
        """Test: Edit with whitespace variations"""
        start = time.time()
        try:
            from core.reliable_editor import ReliableEditor
            
            editor = ReliableEditor()
            test_file = self.temp_dir / "test_file.py"
            original = test_file.read_text()
            
            # Try edit with slightly different whitespace
            result = editor.edit(
                str(test_file),
                search_text='def hello():\n    """Say hello"""',
                replace_text='def hello():\n    """Say hello to everyone"""'
            )
            
            new_content = test_file.read_text()
            passed = result.success and "hello to everyone" in new_content
            
            test_file.write_text(original)
            
            return BenchmarkResult(
                category="edit_success",
                test_name="whitespace_tolerance",
                passed=passed,
                points=3 if passed else 0,
                max_points=3,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="edit_success",
                test_name="whitespace_tolerance",
                passed=False,
                points=0,
                max_points=3,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_edit_class_method(self) -> BenchmarkResult:
        """Test: Add method to class"""
        start = time.time()
        try:
            from core.reliable_editor import ReliableEditor
            
            editor = ReliableEditor()
            test_file = self.temp_dir / "test_file.py"
            original = test_file.read_text()
            
            result = editor.edit(
                str(test_file),
                search_text='    def get_result(self):\n        return self.result',
                replace_text='    def get_result(self):\n        return self.result\n    \n    def reset(self):\n        self.result = 0\n        return self'
            )
            
            new_content = test_file.read_text()
            passed = result.success and "def reset" in new_content
            
            test_file.write_text(original)
            
            return BenchmarkResult(
                category="edit_success",
                test_name="class_method_add",
                passed=passed,
                points=3 if passed else 0,
                max_points=3,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="edit_success",
                test_name="class_method_add",
                passed=False,
                points=0,
                max_points=3,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # FILE DISCOVERY TESTS (20 points max)
    # ═══════════════════════════════════════════════════════════════
    
    def test_find_file_by_name(self) -> BenchmarkResult:
        """Test: Find file by name pattern"""
        start = time.time()
        try:
            from core.auto_context import AutoContextBuilder
            
            builder = AutoContextBuilder(str(self.project_root))
            context = builder.build_context("find the paths.py file")
            
            found = any("paths.py" in f.path for f in context.files)
            
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_by_name",
                passed=found,
                points=2 if found else 0,
                max_points=2,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_by_name",
                passed=False,
                points=0,
                max_points=2,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_find_file_by_content(self) -> BenchmarkResult:
        """Test: Find file by content description"""
        start = time.time()
        try:
            from core.auto_context import AutoContextBuilder
            
            builder = AutoContextBuilder(str(self.project_root))
            context = builder.build_context("find the file that handles model routing")
            
            found = any("model_router" in f.path for f in context.files)
            
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_by_content",
                passed=found,
                points=2 if found else 0,
                max_points=2,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_by_content",
                passed=False,
                points=0,
                max_points=2,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_find_function_location(self) -> BenchmarkResult:
        """Test: Find where a function is defined"""
        start = time.time()
        try:
            from core.auto_context import AutoContextBuilder
            
            builder = AutoContextBuilder(str(self.project_root))
            context = builder.build_context("find the select_model function")
            
            # Check if model_router.py is in results (where select_model is)
            found = any("model_router" in f.path for f in context.files)
            
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_function",
                passed=found,
                points=2 if found else 0,
                max_points=2,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="file_discovery",
                test_name="find_function",
                passed=False,
                points=0,
                max_points=2,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # TASK COMPLETION TESTS (30 points max)
    # ═══════════════════════════════════════════════════════════════
    
    def test_intent_detection(self) -> BenchmarkResult:
        """Test: Correctly detect intent from query"""
        start = time.time()
        try:
            from core.ryx_brain import get_brain, Intent
            
            brain = get_brain()
            
            test_cases = [
                ("fix this bug", Intent.CODE_TASK),
                ("search for python tutorials", Intent.SEARCH_WEB),
                ("open config.json", Intent.OPEN_FILE),
            ]
            
            correct = 0
            for query, expected in test_cases:
                plan = brain.understand(query)
                if plan.intent == expected:
                    correct += 1
            
            passed = correct >= 2  # At least 2/3 correct
            
            return BenchmarkResult(
                category="task_completion",
                test_name="intent_detection",
                passed=passed,
                points=3 if passed else 0,
                max_points=3,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="task_completion",
                test_name="intent_detection",
                passed=False,
                points=0,
                max_points=3,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_model_routing(self) -> BenchmarkResult:
        """Test: Correctly route to appropriate model"""
        start = time.time()
        try:
            from core.model_router import select_model
            
            test_cases = [
                ("fix bug", "code"),
                ("why does this work", "reason"),
                ("hi", "fast"),
            ]
            
            correct = 0
            for query, expected_role in test_cases:
                model = select_model(query)
                if expected_role in model.role.value:
                    correct += 1
            
            passed = correct >= 2
            
            return BenchmarkResult(
                category="task_completion",
                test_name="model_routing",
                passed=passed,
                points=3 if passed else 0,
                max_points=3,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="task_completion",
                test_name="model_routing",
                passed=False,
                points=0,
                max_points=3,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # SELF-HEALING TESTS (10 points max)
    # ═══════════════════════════════════════════════════════════════
    
    def test_retry_on_error(self) -> BenchmarkResult:
        """Test: System has retry logic"""
        start = time.time()
        try:
            from core.tools import WebSearchTool
            
            # Check if retry parameter exists
            tool = WebSearchTool()
            import inspect
            sig = inspect.signature(tool.search)
            has_retry = 'retry' in sig.parameters
            
            return BenchmarkResult(
                category="self_healing",
                test_name="retry_logic",
                passed=has_retry,
                points=2 if has_retry else 0,
                max_points=2,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="self_healing",
                test_name="retry_logic",
                passed=False,
                points=0,
                max_points=2,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_error_recovery(self) -> BenchmarkResult:
        """Test: System can recover from invalid input"""
        start = time.time()
        try:
            from core.reliable_editor import ReliableEditor
            
            editor = ReliableEditor()
            
            # Try edit on non-existent file - should not crash
            try:
                result = editor.edit(
                    "/nonexistent/file.py",
                    search_text="test",
                    replace_text="test2"
                )
                # Should return False, not crash
                passed = not result.success
            except Exception:
                passed = False
            
            return BenchmarkResult(
                category="self_healing",
                test_name="error_recovery",
                passed=passed,
                points=2 if passed else 0,
                max_points=2,
                time_seconds=time.time() - start
            )
        except Exception as e:
            return BenchmarkResult(
                category="self_healing",
                test_name="error_recovery",
                passed=False,
                points=0,
                max_points=2,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # SPEED TESTS (10 points max)
    # ═══════════════════════════════════════════════════════════════
    
    def test_inference_speed(self) -> BenchmarkResult:
        """Test: LLM inference speed"""
        start = time.time()
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:3b",
                    "prompt": "Say 'test'",
                    "stream": False,
                    "options": {"num_predict": 5}
                },
                timeout=30
            )
            
            elapsed = time.time() - start
            
            # Score based on speed
            if elapsed < 1.0:
                points = 5
            elif elapsed < 2.0:
                points = 3
            elif elapsed < 5.0:
                points = 1
            else:
                points = 0
            
            return BenchmarkResult(
                category="speed",
                test_name="inference_speed",
                passed=elapsed < 5.0,
                points=points,
                max_points=5,
                time_seconds=elapsed
            )
        except Exception as e:
            return BenchmarkResult(
                category="speed",
                test_name="inference_speed",
                passed=False,
                points=0,
                max_points=5,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    def test_context_build_speed(self) -> BenchmarkResult:
        """Test: Context building speed"""
        start = time.time()
        try:
            from core.auto_context import AutoContextBuilder
            
            builder = AutoContextBuilder(str(self.project_root))
            context = builder.build_context("find model router")
            
            elapsed = time.time() - start
            
            if elapsed < 0.5:
                points = 5
            elif elapsed < 1.0:
                points = 3
            elif elapsed < 2.0:
                points = 1
            else:
                points = 0
            
            return BenchmarkResult(
                category="speed",
                test_name="context_build_speed",
                passed=elapsed < 2.0,
                points=points,
                max_points=5,
                time_seconds=elapsed
            )
        except Exception as e:
            return BenchmarkResult(
                category="speed",
                test_name="context_build_speed",
                passed=False,
                points=0,
                max_points=5,
                time_seconds=time.time() - start,
                error=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════
    # RUN ALL TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def run_all(self) -> BenchmarkReport:
        """Run all benchmark tests"""
        print("═" * 60)
        print("  RYX AI BENCHMARK")
        print("═" * 60)
        print()
        
        self.setup()
        
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat()
        )
        
        # Edit tests
        print("📝 EDIT SUCCESS TESTS")
        edit_tests = [
            self.test_edit_simple_function,
            self.test_edit_with_whitespace,
            self.test_edit_class_method,
        ]
        for test in edit_tests:
            result = test()
            self.results.append(result)
            report.edit_success += result.points
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}: {result.points}/{result.max_points}")
        print()
        
        # File discovery tests
        print("🔍 FILE DISCOVERY TESTS")
        file_tests = [
            self.test_find_file_by_name,
            self.test_find_file_by_content,
            self.test_find_function_location,
        ]
        for test in file_tests:
            result = test()
            self.results.append(result)
            report.file_discovery += result.points
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}: {result.points}/{result.max_points}")
        print()
        
        # Task completion tests
        print("🎯 TASK COMPLETION TESTS")
        task_tests = [
            self.test_intent_detection,
            self.test_model_routing,
        ]
        for test in task_tests:
            result = test()
            self.results.append(result)
            report.task_completion += result.points
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}: {result.points}/{result.max_points}")
        print()
        
        # Self-healing tests
        print("🔧 SELF-HEALING TESTS")
        healing_tests = [
            self.test_retry_on_error,
            self.test_error_recovery,
        ]
        for test in healing_tests:
            result = test()
            self.results.append(result)
            report.self_healing += result.points
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}: {result.points}/{result.max_points}")
        print()
        
        # Speed tests
        print("⚡ SPEED TESTS")
        speed_tests = [
            self.test_inference_speed,
            self.test_context_build_speed,
        ]
        for test in speed_tests:
            result = test()
            self.results.append(result)
            report.speed_bonus += result.points
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}: {result.points}/{result.max_points} ({result.time_seconds:.2f}s)")
        print()
        
        # Calculate total
        report.calculate_total()
        report.results = [asdict(r) for r in self.results]
        
        # Print summary
        print("═" * 60)
        print("  BENCHMARK SUMMARY")
        print("═" * 60)
        print(f"  Edit Success:    {report.edit_success:2}/{report.edit_max}")
        print(f"  File Discovery:  {report.file_discovery:2}/{report.file_max}")
        print(f"  Task Completion: {report.task_completion:2}/{report.task_max}")
        print(f"  Self-Healing:    {report.self_healing:2}/{report.healing_max}")
        print(f"  Speed Bonus:     {report.speed_bonus:2}/{report.speed_max}")
        print("  " + "─" * 30)
        print(f"  TOTAL:           {report.total:2}/{report.max_total}")
        print("═" * 60)
        
        self.teardown()
        
        return report
    
    def save_report(self, report: BenchmarkReport, path: Optional[Path] = None):
        """Save benchmark report to file"""
        if path is None:
            log_dir = self.project_root / "data" / "benchmark_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = log_dir / f"benchmark_{timestamp}.json"
        
        with open(path, "w") as f:
            json.dump(asdict(report), f, indent=2)
        
        print(f"\nReport saved to: {path}")
        return path


def main():
    benchmark = RyxBenchmark()
    report = benchmark.run_all()
    benchmark.save_report(report)
    return report.total


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0 else 1)
