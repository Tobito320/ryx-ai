"""
Hallucination Detector for Ryx.

Detects when the LLM hallucinates:
- Non-existent file paths
- Non-installed packages
- Invalid imports
- Fabricated functions/classes

Inspired by Claude Code's validation patterns.
"""

import os
import re
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class HallucinationReport:
    """Report of detected hallucinations."""
    is_clean: bool = True
    invalid_paths: List[str] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)
    invalid_imports: List[str] = field(default_factory=list)
    suggestions: Dict[str, str] = field(default_factory=dict)  # hallucinated -> suggested
    
    @property
    def has_issues(self) -> bool:
        return bool(self.invalid_paths or self.missing_packages or self.invalid_imports)
    
    def summary(self) -> str:
        if not self.has_issues:
            return "✓ No hallucinations detected"
        
        lines = ["⚠️ Hallucinations detected:"]
        if self.invalid_paths:
            lines.append(f"  - Invalid paths: {', '.join(self.invalid_paths[:5])}")
        if self.missing_packages:
            lines.append(f"  - Missing packages: {', '.join(self.missing_packages[:5])}")
        if self.invalid_imports:
            lines.append(f"  - Invalid imports: {', '.join(self.invalid_imports[:5])}")
        if self.suggestions:
            lines.append("  Suggestions:")
            for wrong, right in list(self.suggestions.items())[:3]:
                lines.append(f"    - '{wrong}' → Did you mean '{right}'?")
        return "\n".join(lines)


class HallucinationDetector:
    """
    Detects hallucinated paths, packages, and imports.
    
    Usage:
        detector = HallucinationDetector()
        report = detector.check_response(llm_response)
        if report.has_issues:
            print(report.summary())
    """
    
    # Common package name mappings (pypi name -> import name)
    PACKAGE_MAPPINGS = {
        'pillow': 'PIL',
        'opencv-python': 'cv2',
        'scikit-learn': 'sklearn',
        'beautifulsoup4': 'bs4',
        'pyyaml': 'yaml',
        'python-dotenv': 'dotenv',
    }
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or os.getcwd())
        self._installed_packages: Optional[Set[str]] = None
        self._file_cache: Set[str] = set()
        self._refresh_file_cache()
    
    def _refresh_file_cache(self):
        """Cache all existing files for fast lookup."""
        self._file_cache.clear()
        try:
            for root, _, files in os.walk(self.root_path):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), self.root_path)
                    self._file_cache.add(rel_path)
                    self._file_cache.add(os.path.join(root, f))
        except Exception:
            pass
    
    def _get_installed_packages(self) -> Set[str]:
        """Get set of installed Python packages."""
        if self._installed_packages is not None:
            return self._installed_packages
        
        self._installed_packages = set()
        try:
            result = subprocess.run(
                ['pip', 'list', '--format=freeze'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    pkg = line.split('==')[0].lower()
                    self._installed_packages.add(pkg)
        except Exception:
            pass
        
        # Add standard library modules
        import sys
        self._installed_packages.update(sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else set())
        
        return self._installed_packages
    
    def check_response(self, response: str) -> HallucinationReport:
        """
        Check an LLM response for hallucinations.
        
        Args:
            response: The LLM's text response
            
        Returns:
            HallucinationReport with detected issues
        """
        report = HallucinationReport()
        
        # Extract and check file paths
        paths = self._extract_paths(response)
        for path in paths:
            if not self._path_exists(path):
                report.invalid_paths.append(path)
                suggestion = self._find_similar_path(path)
                if suggestion:
                    report.suggestions[path] = suggestion
        
        # Extract and check code blocks for imports
        code_blocks = self._extract_code_blocks(response)
        for code in code_blocks:
            imports = self._extract_imports(code)
            for imp in imports:
                if not self._package_installed(imp):
                    report.missing_packages.append(imp)
        
        report.is_clean = not report.has_issues
        return report
    
    def check_paths(self, paths: List[str]) -> HallucinationReport:
        """Check a list of paths for existence."""
        report = HallucinationReport()
        
        for path in paths:
            if not self._path_exists(path):
                report.invalid_paths.append(path)
                suggestion = self._find_similar_path(path)
                if suggestion:
                    report.suggestions[path] = suggestion
        
        report.is_clean = not report.has_issues
        return report
    
    def check_code(self, code: str) -> HallucinationReport:
        """Check code for missing imports/packages."""
        report = HallucinationReport()
        
        imports = self._extract_imports(code)
        for imp in imports:
            if not self._package_installed(imp):
                report.missing_packages.append(imp)
        
        report.is_clean = not report.has_issues
        return report
    
    def _extract_paths(self, text: str) -> List[str]:
        """Extract file paths from text."""
        paths = []
        
        # Match paths in backticks: `path/to/file.py`
        backtick_paths = re.findall(r'`([^`]+\.[a-zA-Z0-9]+)`', text)
        paths.extend(backtick_paths)
        
        # Match paths in quotes: "path/to/file.py" or 'path/to/file.py'
        quoted_paths = re.findall(r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']', text)
        paths.extend(quoted_paths)
        
        # Match common path patterns
        path_patterns = re.findall(r'(?:^|\s)((?:\w+/)+\w+\.\w+)', text, re.MULTILINE)
        paths.extend(path_patterns)
        
        # Filter to likely file paths
        valid_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml', 
                          '.md', '.txt', '.html', '.css', '.sh', '.go', '.rs', '.toml'}
        
        filtered = []
        for p in paths:
            p = p.strip()
            ext = os.path.splitext(p)[1].lower()
            if ext in valid_extensions and not p.startswith(('http://', 'https://')):
                filtered.append(p)
        
        return list(set(filtered))
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from markdown."""
        # Match ```python ... ``` or ``` ... ```
        blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.DOTALL)
        return blocks
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import names from Python code."""
        imports = set()
        
        # Try AST parsing first
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except SyntaxError:
            # Fallback to regex
            import_matches = re.findall(r'^(?:from\s+(\w+)|import\s+(\w+))', code, re.MULTILINE)
            for match in import_matches:
                pkg = match[0] or match[1]
                if pkg:
                    imports.add(pkg)
        
        return list(imports)
    
    def _path_exists(self, path: str) -> bool:
        """Check if a path exists."""
        # Check absolute path
        if os.path.isabs(path):
            return os.path.exists(path)
        
        # Check relative to root
        full_path = self.root_path / path
        if full_path.exists():
            return True
        
        # Check in cache
        if path in self._file_cache:
            return True
        
        return False
    
    def _find_similar_path(self, path: str) -> Optional[str]:
        """Find a similar existing path (for suggestions)."""
        filename = os.path.basename(path)
        
        # Look for files with the same name
        for cached_path in self._file_cache:
            if os.path.basename(cached_path) == filename:
                return cached_path
        
        # Look for similar filenames (fuzzy match)
        import difflib
        cached_list = list(self._file_cache)
        matches = difflib.get_close_matches(filename, 
                                            [os.path.basename(p) for p in cached_list],
                                            n=1, cutoff=0.6)
        if matches:
            for cached_path in cached_list:
                if os.path.basename(cached_path) == matches[0]:
                    return cached_path
        
        return None
    
    def _package_installed(self, package: str) -> bool:
        """Check if a Python package is installed."""
        installed = self._get_installed_packages()
        
        # Direct check
        if package.lower() in installed:
            return True
        
        # Check mappings
        for pypi_name, import_name in self.PACKAGE_MAPPINGS.items():
            if package == import_name and pypi_name in installed:
                return True
        
        # Standard library check
        try:
            __import__(package)
            return True
        except ImportError:
            pass
        
        return False


# Convenience function
def detect_hallucinations(response: str, root_path: Optional[str] = None) -> HallucinationReport:
    """Quick check for hallucinations in LLM response."""
    detector = HallucinationDetector(root_path)
    return detector.check_response(response)
