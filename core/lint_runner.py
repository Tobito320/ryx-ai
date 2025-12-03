"""
Lint Runner for Ryx.

Auto-detects and runs linters/formatters for various languages.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LintSeverity(Enum):
    """Severity levels for lint issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    """A single lint issue."""
    file: str
    line: int
    column: int
    severity: LintSeverity
    code: str  # e.g., E501, W0612
    message: str
    
    def __str__(self):
        return f"{self.file}:{self.line}:{self.column}: [{self.code}] {self.message}"


@dataclass
class LintResult:
    """Result from running a linter."""
    success: bool
    linter: str
    issues: List[LintIssue] = field(default_factory=list)
    raw_output: str = ""
    error_count: int = 0
    warning_count: int = 0
    fixed_count: int = 0  # If auto-fix was applied
    
    @property
    def has_errors(self) -> bool:
        return self.error_count > 0
    
    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0
    
    def summary(self) -> str:
        if self.success and not self.has_errors and not self.has_warnings:
            return f"✓ {self.linter}: No issues found"
        
        parts = [f"{self.linter}:"]
        if self.error_count:
            parts.append(f"{self.error_count} errors")
        if self.warning_count:
            parts.append(f"{self.warning_count} warnings")
        if self.fixed_count:
            parts.append(f"{self.fixed_count} fixed")
        
        return " ".join(parts)


@dataclass
class LinterConfig:
    """Configuration for a linter."""
    name: str
    command: List[str]
    check_command: List[str]  # Command to check without fixing
    fix_command: Optional[List[str]] = None  # Command to auto-fix
    file_patterns: List[str] = field(default_factory=list)  # e.g., ["*.py"]
    parse_output: Optional[callable] = None


class LintRunner:
    """
    Detects and runs linters for the project.
    
    Usage:
        runner = LintRunner()
        result = runner.lint_files(["src/main.py"])
        if result.has_errors:
            print(result.summary())
    """
    
    # Available linters with their configurations
    LINTERS: Dict[str, LinterConfig] = {}
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or os.getcwd())
        self._detected_linters: Dict[str, LinterConfig] = {}
        self._setup_linters()
        self._detect_available_linters()
    
    def _setup_linters(self):
        """Setup linter configurations."""
        # Python linters
        self.LINTERS['ruff'] = LinterConfig(
            name='ruff',
            command=['ruff', 'check'],
            check_command=['ruff', 'check'],
            fix_command=['ruff', 'check', '--fix'],
            file_patterns=['*.py'],
        )
        
        self.LINTERS['black'] = LinterConfig(
            name='black',
            command=['black', '--check'],
            check_command=['black', '--check', '--diff'],
            fix_command=['black'],
            file_patterns=['*.py'],
        )
        
        self.LINTERS['pylint'] = LinterConfig(
            name='pylint',
            command=['pylint'],
            check_command=['pylint', '--output-format=text'],
            file_patterns=['*.py'],
        )
        
        self.LINTERS['flake8'] = LinterConfig(
            name='flake8',
            command=['flake8'],
            check_command=['flake8'],
            file_patterns=['*.py'],
        )
        
        self.LINTERS['mypy'] = LinterConfig(
            name='mypy',
            command=['mypy'],
            check_command=['mypy'],
            file_patterns=['*.py'],
        )
        
        # JavaScript/TypeScript linters
        self.LINTERS['eslint'] = LinterConfig(
            name='eslint',
            command=['npx', 'eslint'],
            check_command=['npx', 'eslint'],
            fix_command=['npx', 'eslint', '--fix'],
            file_patterns=['*.js', '*.jsx', '*.ts', '*.tsx'],
        )
        
        self.LINTERS['prettier'] = LinterConfig(
            name='prettier',
            command=['npx', 'prettier', '--check'],
            check_command=['npx', 'prettier', '--check'],
            fix_command=['npx', 'prettier', '--write'],
            file_patterns=['*.js', '*.jsx', '*.ts', '*.tsx', '*.json', '*.css', '*.md'],
        )
        
        # Go linters
        self.LINTERS['golangci-lint'] = LinterConfig(
            name='golangci-lint',
            command=['golangci-lint', 'run'],
            check_command=['golangci-lint', 'run'],
            file_patterns=['*.go'],
        )
        
        # Rust linters
        self.LINTERS['clippy'] = LinterConfig(
            name='clippy',
            command=['cargo', 'clippy'],
            check_command=['cargo', 'clippy', '--', '-D', 'warnings'],
            file_patterns=['*.rs'],
        )
    
    def _detect_available_linters(self):
        """Detect which linters are available on the system."""
        for name, config in self.LINTERS.items():
            cmd = config.command[0]
            if cmd == 'npx':
                # Check if node_modules exists
                if (self.root_path / 'node_modules').exists():
                    self._detected_linters[name] = config
            elif shutil.which(cmd):
                self._detected_linters[name] = config
    
    def detect_project_linter(self) -> Optional[str]:
        """Detect the appropriate linter for the project."""
        # Check for config files
        configs = {
            'ruff': ['ruff.toml', 'pyproject.toml'],
            'black': ['pyproject.toml', '.black'],
            'pylint': ['.pylintrc', 'pyproject.toml'],
            'flake8': ['.flake8', 'setup.cfg'],
            'eslint': ['.eslintrc', '.eslintrc.js', '.eslintrc.json'],
            'prettier': ['.prettierrc', '.prettierrc.js', 'prettier.config.js'],
        }
        
        for linter, files in configs.items():
            for f in files:
                if (self.root_path / f).exists():
                    if linter in self._detected_linters:
                        return linter
        
        # Default based on file types
        py_files = list(self.root_path.rglob('*.py'))
        if py_files:
            # Prefer ruff, then black, then flake8
            for linter in ['ruff', 'black', 'flake8', 'pylint']:
                if linter in self._detected_linters:
                    return linter
        
        js_files = list(self.root_path.rglob('*.js')) + list(self.root_path.rglob('*.ts'))
        if js_files:
            for linter in ['eslint', 'prettier']:
                if linter in self._detected_linters:
                    return linter
        
        return None
    
    def lint_files(self, files: List[str], fix: bool = False, 
                   linter: Optional[str] = None) -> LintResult:
        """
        Lint specified files.
        
        Args:
            files: List of file paths to lint
            fix: Whether to auto-fix issues
            linter: Specific linter to use (auto-detect if None)
            
        Returns:
            LintResult with issues found
        """
        if not files:
            return LintResult(success=True, linter="none", raw_output="No files to lint")
        
        # Determine linter to use
        if linter:
            if linter not in self._detected_linters:
                return LintResult(
                    success=False, 
                    linter=linter, 
                    raw_output=f"Linter '{linter}' not available"
                )
            config = self._detected_linters[linter]
        else:
            detected = self.detect_project_linter()
            if not detected:
                return LintResult(
                    success=True, 
                    linter="none", 
                    raw_output="No suitable linter detected"
                )
            config = self._detected_linters[detected]
        
        # Filter files by pattern
        matching_files = self._filter_files(files, config.file_patterns)
        if not matching_files:
            return LintResult(
                success=True, 
                linter=config.name, 
                raw_output="No matching files for linter"
            )
        
        # Run linter
        cmd = config.fix_command if fix and config.fix_command else config.check_command
        return self._run_linter(config.name, cmd, matching_files)
    
    def lint_directory(self, path: str = ".", fix: bool = False,
                      linter: Optional[str] = None) -> LintResult:
        """Lint all files in a directory."""
        target = self.root_path / path
        if not target.exists():
            return LintResult(
                success=False, 
                linter=linter or "unknown", 
                raw_output=f"Directory not found: {path}"
            )
        
        # Collect all source files
        files = []
        for pattern in ['*.py', '*.js', '*.ts', '*.tsx', '*.go', '*.rs']:
            files.extend(str(f) for f in target.rglob(pattern))
        
        return self.lint_files(files, fix=fix, linter=linter)
    
    def _filter_files(self, files: List[str], patterns: List[str]) -> List[str]:
        """Filter files by patterns."""
        import fnmatch
        
        matching = []
        for f in files:
            for pattern in patterns:
                if fnmatch.fnmatch(os.path.basename(f), pattern):
                    matching.append(f)
                    break
        return matching
    
    def _run_linter(self, name: str, cmd: List[str], files: List[str]) -> LintResult:
        """Run a linter command."""
        try:
            full_cmd = cmd + files
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=str(self.root_path),
                timeout=120
            )
            
            # Parse output
            issues, errors, warnings = self._parse_output(name, result.stdout + result.stderr)
            
            return LintResult(
                success=result.returncode == 0,
                linter=name,
                issues=issues,
                raw_output=result.stdout + result.stderr,
                error_count=errors,
                warning_count=warnings,
            )
            
        except subprocess.TimeoutExpired:
            return LintResult(
                success=False,
                linter=name,
                raw_output="Linter timed out after 120 seconds"
            )
        except Exception as e:
            return LintResult(
                success=False,
                linter=name,
                raw_output=f"Linter error: {e}"
            )
    
    def _parse_output(self, linter: str, output: str) -> Tuple[List[LintIssue], int, int]:
        """Parse linter output into structured issues."""
        issues = []
        errors = 0
        warnings = 0
        
        for line in output.split('\n'):
            issue = self._parse_line(linter, line)
            if issue:
                issues.append(issue)
                if issue.severity == LintSeverity.ERROR:
                    errors += 1
                elif issue.severity == LintSeverity.WARNING:
                    warnings += 1
        
        return issues, errors, warnings
    
    def _parse_line(self, linter: str, line: str) -> Optional[LintIssue]:
        """Parse a single line of linter output."""
        import re
        
        # Common format: file:line:col: code message
        match = re.match(r'^([^:]+):(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)$', line)
        if match:
            severity = LintSeverity.ERROR if match.group(4).startswith('E') else LintSeverity.WARNING
            return LintIssue(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                severity=severity,
                code=match.group(4),
                message=match.group(5),
            )
        
        # Ruff/flake8 format: file:line:col: code message
        match = re.match(r'^([^:]+):(\d+):(\d+):\s*(.+)$', line)
        if match:
            return LintIssue(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                severity=LintSeverity.WARNING,
                code="",
                message=match.group(4),
            )
        
        return None
    
    def get_available_linters(self) -> List[str]:
        """Get list of available linters."""
        return list(self._detected_linters.keys())


# Convenience functions
def lint_files(files: List[str], fix: bool = False) -> LintResult:
    """Quick lint files."""
    return LintRunner().lint_files(files, fix=fix)

def detect_linter() -> Optional[str]:
    """Quick detect project linter."""
    return LintRunner().detect_project_linter()
