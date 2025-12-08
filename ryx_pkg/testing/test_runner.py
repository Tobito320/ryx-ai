"""
Ryx Test Runner

Execute tests and parse results for verification.
Supports pytest, jest, go test, and custom test commands.
"""

import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TestCase:
    """A single test case result"""
    name: str
    status: TestStatus
    duration_ms: float = 0
    message: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None


@dataclass
class TestResult:
    """Result of a test run"""
    success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0
    output: str = ""
    tests: List[TestCase] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        """Get a summary string"""
        if self.success:
            return f"✓ {self.passed}/{self.total} tests passed"
        return f"✗ {self.failed} failed, {self.passed} passed ({self.total} total)"


class TestRunner:
    """
    Test runner for Ryx.
    
    Supports:
    - pytest (Python)
    - jest/npm test (JavaScript/TypeScript)
    - go test (Go)
    - cargo test (Rust)
    - Custom commands
    """
    
    # Default test commands by framework
    FRAMEWORKS = {
        'pytest': {
            'cmd': ['pytest', '-v', '--tb=short'],
            'markers': ['pytest.ini', 'pyproject.toml', 'setup.py', 'tests/'],
            'pattern': r'(tests?/|test_\w+\.py|\w+_test\.py)'
        },
        'jest': {
            'cmd': ['npm', 'test', '--'],
            'markers': ['jest.config.js', 'jest.config.ts', 'package.json'],
            'pattern': r'(__tests__/|\.test\.[jt]sx?|\.spec\.[jt]sx?)'
        },
        'go': {
            'cmd': ['go', 'test', '-v', './...'],
            'markers': ['go.mod', 'go.sum'],
            'pattern': r'_test\.go$'
        },
        'cargo': {
            'cmd': ['cargo', 'test'],
            'markers': ['Cargo.toml'],
            'pattern': r'(tests/|#\[test\])'
        }
    }
    
    def __init__(
        self,
        root: str = None,
        framework: str = None,
        timeout: int = 300
    ):
        """
        Initialize TestRunner.
        
        Args:
            root: Project root directory
            framework: Test framework (auto-detect if None)
            timeout: Test timeout in seconds
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.timeout = timeout
        self._custom_cmd = None
        self._manifest = None
        
        # Try to load manifest for test command (P1.7)
        try:
            from core.manifest import ManifestLoader
            loader = ManifestLoader(str(self.root))
            self._manifest = loader.load()
            
            # Use manifest test command if available
            if self._manifest and self._manifest.test_command:
                self._custom_cmd = self._manifest.test_command.split()
                logger.debug(f"Using manifest test command: {self._manifest.test_command}")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Could not load manifest: {e}")
        
        self.framework = framework or self._detect_framework()
    
    def _detect_framework(self) -> Optional[str]:
        """Auto-detect test framework"""
        for name, config in self.FRAMEWORKS.items():
            for marker in config['markers']:
                marker_path = self.root / marker
                if marker_path.exists():
                    logger.debug(f"Detected framework: {name}")
                    return name
        return None
    
    def set_custom_command(self, cmd: List[str]):
        """Set a custom test command"""
        self._custom_cmd = cmd
    
    def run(
        self,
        files: List[str] = None,
        pattern: str = None,
        verbose: bool = False
    ) -> TestResult:
        """
        Run tests.
        
        Args:
            files: Specific test files to run
            pattern: Test name pattern
            verbose: Verbose output
            
        Returns:
            TestResult with details
        """
        cmd = self._build_command(files, pattern)
        
        if not cmd:
            return TestResult(
                success=False,
                output="No test framework detected and no custom command set"
            )
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            # Parse results based on framework
            parsed = self._parse_output(output, success)
            parsed.output = output
            
            return parsed
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                output=f"Test timeout after {self.timeout}s"
            )
        except FileNotFoundError as e:
            return TestResult(
                success=False,
                output=f"Command not found: {e}"
            )
        except Exception as e:
            return TestResult(
                success=False,
                output=f"Error running tests: {e}"
            )
    
    def _build_command(
        self,
        files: List[str] = None,
        pattern: str = None
    ) -> Optional[List[str]]:
        """Build the test command"""
        if self._custom_cmd:
            cmd = list(self._custom_cmd)
        elif self.framework and self.framework in self.FRAMEWORKS:
            cmd = list(self.FRAMEWORKS[self.framework]['cmd'])
        else:
            return None
        
        # Add file arguments
        if files:
            if self.framework == 'pytest':
                cmd.extend(files)
            elif self.framework == 'jest':
                cmd.extend(['--testPathPattern', '|'.join(files)])
            elif self.framework == 'go':
                cmd = ['go', 'test', '-v'] + files
            else:
                cmd.extend(files)
        
        # Add pattern filter
        if pattern:
            if self.framework == 'pytest':
                cmd.extend(['-k', pattern])
            elif self.framework == 'jest':
                cmd.extend(['--testNamePattern', pattern])
            elif self.framework == 'go':
                cmd.extend(['-run', pattern])
        
        return cmd
    
    def _parse_output(self, output: str, success: bool) -> TestResult:
        """Parse test output into structured result"""
        result = TestResult(success=success)
        
        if self.framework == 'pytest':
            result = self._parse_pytest(output, success)
        elif self.framework == 'jest':
            result = self._parse_jest(output, success)
        elif self.framework == 'go':
            result = self._parse_go(output, success)
        else:
            # Generic parsing
            result = self._parse_generic(output, success)
        
        return result
    
    def _parse_pytest(self, output: str, success: bool) -> TestResult:
        """Parse pytest output"""
        result = TestResult(success=success)
        
        # Parse summary line: "=== X passed, Y failed, Z skipped in N.NNs ==="
        summary_match = re.search(
            r'(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?.*?in\s+([\d.]+)',
            output
        )
        
        if summary_match:
            result.passed = int(summary_match.group(1))
            result.failed = int(summary_match.group(2) or 0)
            result.skipped = int(summary_match.group(3) or 0)
            result.duration_ms = float(summary_match.group(4)) * 1000
            result.total = result.passed + result.failed + result.skipped
            
            # Override success based on actual test results, not just exit code
            # If we parsed results and failed=0, consider it success
            if result.failed == 0 and result.passed > 0:
                result.success = True
        
        # Parse individual test results
        for match in re.finditer(r'(\S+::\S+)\s+(PASSED|FAILED|SKIPPED)', output):
            test_name = match.group(1)
            status_str = match.group(2)
            
            status = {
                'PASSED': TestStatus.PASSED,
                'FAILED': TestStatus.FAILED,
                'SKIPPED': TestStatus.SKIPPED
            }.get(status_str, TestStatus.UNKNOWN)
            
            result.tests.append(TestCase(
                name=test_name,
                status=status
            ))
        
        # Parse failure details
        for match in re.finditer(
            r'FAILED\s+(\S+)\s+-\s+(.+?)(?=\n(?:FAILED|===|$))',
            output,
            re.DOTALL
        ):
            test_name = match.group(1)
            message = match.group(2).strip()[:200]
            
            # Find the test case and add message
            for test in result.tests:
                if test.name == test_name:
                    test.message = message
                    break
        
        return result
    
    def _parse_jest(self, output: str, success: bool) -> TestResult:
        """Parse jest output"""
        result = TestResult(success=success)
        
        # Parse summary: "Tests: X passed, Y failed, Z total"
        summary_match = re.search(
            r'Tests:\s+(?:(\d+)\s+failed,\s+)?(?:(\d+)\s+passed,\s+)?(\d+)\s+total',
            output
        )
        
        if summary_match:
            result.failed = int(summary_match.group(1) or 0)
            result.passed = int(summary_match.group(2) or 0)
            result.total = int(summary_match.group(3))
        
        # Parse individual tests
        for match in re.finditer(r'(✓|✕|○)\s+(.+?)(?:\s+\((\d+)\s*ms\))?$', output, re.MULTILINE):
            symbol = match.group(1)
            name = match.group(2)
            duration = int(match.group(3) or 0)
            
            status = {
                '✓': TestStatus.PASSED,
                '✕': TestStatus.FAILED,
                '○': TestStatus.SKIPPED
            }.get(symbol, TestStatus.UNKNOWN)
            
            result.tests.append(TestCase(
                name=name,
                status=status,
                duration_ms=duration
            ))
        
        return result
    
    def _parse_go(self, output: str, success: bool) -> TestResult:
        """Parse go test output"""
        result = TestResult(success=success)
        
        # Parse test results: "--- PASS: TestName (0.00s)" or "--- FAIL: ..."
        for match in re.finditer(r'---\s+(PASS|FAIL|SKIP):\s+(\S+)\s+\(([\d.]+)s\)', output):
            status_str = match.group(1)
            name = match.group(2)
            duration = float(match.group(3)) * 1000
            
            status = {
                'PASS': TestStatus.PASSED,
                'FAIL': TestStatus.FAILED,
                'SKIP': TestStatus.SKIPPED
            }.get(status_str, TestStatus.UNKNOWN)
            
            result.tests.append(TestCase(
                name=name,
                status=status,
                duration_ms=duration
            ))
            
            if status == TestStatus.PASSED:
                result.passed += 1
            elif status == TestStatus.FAILED:
                result.failed += 1
            elif status == TestStatus.SKIPPED:
                result.skipped += 1
        
        result.total = len(result.tests)
        
        return result
    
    def _parse_generic(self, output: str, success: bool) -> TestResult:
        """Generic test output parsing"""
        result = TestResult(success=success)
        
        # Count common patterns
        result.passed = len(re.findall(r'\b(PASS|OK|✓|passed)\b', output, re.I))
        result.failed = len(re.findall(r'\b(FAIL|ERROR|✗|failed)\b', output, re.I))
        result.total = result.passed + result.failed
        
        return result
    
    def run_for_files(self, changed_files: List[str]) -> TestResult:
        """
        Run tests related to changed files.
        
        Args:
            changed_files: List of changed file paths
            
        Returns:
            TestResult
        """
        test_files = []
        
        if not self.framework or self.framework not in self.FRAMEWORKS:
            return self.run()
        
        pattern = self.FRAMEWORKS[self.framework]['pattern']
        
        for f in changed_files:
            # If it's already a test file, include it
            if re.search(pattern, f):
                test_files.append(f)
            else:
                # Try to find associated test file
                test_file = self._find_test_file(f)
                if test_file:
                    test_files.append(test_file)
        
        if test_files:
            return self.run(files=list(set(test_files)))
        
        # No specific tests found, run all
        return self.run()
    
    def _find_test_file(self, file_path: str) -> Optional[str]:
        """Find test file for a source file"""
        path = Path(file_path)
        stem = path.stem
        suffix = path.suffix
        
        # Common test file naming patterns
        patterns = [
            f"test_{stem}{suffix}",
            f"{stem}_test{suffix}",
            f"tests/test_{stem}{suffix}",
            f"tests/{stem}_test{suffix}",
            f"__tests__/{stem}.test{suffix}",
            f"__tests__/{stem}.spec{suffix}",
        ]
        
        for pattern in patterns:
            test_path = self.root / pattern
            if test_path.exists():
                return str(test_path.relative_to(self.root))
        
        return None
