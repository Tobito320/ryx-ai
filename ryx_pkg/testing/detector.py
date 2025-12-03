"""
Ryx Test Framework Detector

Auto-detect test framework and configuration.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FrameworkInfo:
    """Information about a detected test framework"""
    name: str
    config_file: Optional[str] = None
    test_command: Optional[List[str]] = None
    test_directory: Optional[str] = None
    patterns: List[str] = None
    
    def __post_init__(self):
        if self.patterns is None:
            self.patterns = []


class TestDetector:
    """
    Detect test framework and configuration.
    
    Supports:
    - pytest (Python)
    - unittest (Python)
    - jest (JavaScript/TypeScript)
    - mocha (JavaScript)
    - go test (Go)
    - cargo test (Rust)
    - dotnet test (.NET)
    """
    
    def __init__(self, root: str = None):
        """
        Initialize TestDetector.
        
        Args:
            root: Project root directory
        """
        self.root = Path(root or os.getcwd()).resolve()
    
    def detect(self) -> Optional[FrameworkInfo]:
        """
        Detect the test framework.
        
        Returns:
            FrameworkInfo if detected, None otherwise
        """
        # Try each detector in order
        detectors = [
            self._detect_pytest,
            self._detect_jest,
            self._detect_mocha,
            self._detect_go,
            self._detect_cargo,
            self._detect_dotnet,
        ]
        
        for detector in detectors:
            result = detector()
            if result:
                return result
        
        return None
    
    def _detect_pytest(self) -> Optional[FrameworkInfo]:
        """Detect pytest"""
        # Check for pytest.ini
        pytest_ini = self.root / 'pytest.ini'
        if pytest_ini.exists():
            return FrameworkInfo(
                name='pytest',
                config_file=str(pytest_ini),
                test_command=['pytest', '-v'],
                patterns=['test_*.py', '*_test.py', 'tests/']
            )
        
        # Check for [tool.pytest] in pyproject.toml
        pyproject = self.root / 'pyproject.toml'
        if pyproject.exists():
            content = pyproject.read_text()
            if '[tool.pytest' in content:
                return FrameworkInfo(
                    name='pytest',
                    config_file=str(pyproject),
                    test_command=['pytest', '-v'],
                    patterns=['test_*.py', '*_test.py', 'tests/']
                )
        
        # Check for conftest.py or tests directory
        if (self.root / 'conftest.py').exists() or (self.root / 'tests').is_dir():
            return FrameworkInfo(
                name='pytest',
                test_command=['pytest', '-v'],
                test_directory='tests',
                patterns=['test_*.py', '*_test.py']
            )
        
        return None
    
    def _detect_jest(self) -> Optional[FrameworkInfo]:
        """Detect Jest"""
        # Check for jest.config.js/ts
        for config in ['jest.config.js', 'jest.config.ts', 'jest.config.mjs']:
            config_path = self.root / config
            if config_path.exists():
                return FrameworkInfo(
                    name='jest',
                    config_file=str(config_path),
                    test_command=['npm', 'test'],
                    patterns=['*.test.js', '*.test.ts', '*.spec.js', '*.spec.ts', '__tests__/']
                )
        
        # Check package.json for jest config
        package_json = self.root / 'package.json'
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                
                if 'jest' in data:
                    return FrameworkInfo(
                        name='jest',
                        config_file=str(package_json),
                        test_command=['npm', 'test'],
                        patterns=['*.test.js', '*.test.ts', '__tests__/']
                    )
                
                # Check scripts for jest
                scripts = data.get('scripts', {})
                if 'test' in scripts and 'jest' in scripts['test']:
                    return FrameworkInfo(
                        name='jest',
                        config_file=str(package_json),
                        test_command=['npm', 'test'],
                        patterns=['*.test.js', '*.test.ts', '__tests__/']
                    )
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _detect_mocha(self) -> Optional[FrameworkInfo]:
        """Detect Mocha"""
        mocharc = self.root / '.mocharc.json'
        if mocharc.exists():
            return FrameworkInfo(
                name='mocha',
                config_file=str(mocharc),
                test_command=['npm', 'test'],
                patterns=['*.test.js', '*.spec.js', 'test/']
            )
        
        package_json = self.root / 'package.json'
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                scripts = data.get('scripts', {})
                if 'test' in scripts and 'mocha' in scripts['test']:
                    return FrameworkInfo(
                        name='mocha',
                        config_file=str(package_json),
                        test_command=['npm', 'test'],
                        patterns=['*.test.js', '*.spec.js', 'test/']
                    )
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _detect_go(self) -> Optional[FrameworkInfo]:
        """Detect Go testing"""
        go_mod = self.root / 'go.mod'
        if go_mod.exists():
            return FrameworkInfo(
                name='go',
                config_file=str(go_mod),
                test_command=['go', 'test', '-v', './...'],
                patterns=['*_test.go']
            )
        
        return None
    
    def _detect_cargo(self) -> Optional[FrameworkInfo]:
        """Detect Cargo/Rust testing"""
        cargo_toml = self.root / 'Cargo.toml'
        if cargo_toml.exists():
            return FrameworkInfo(
                name='cargo',
                config_file=str(cargo_toml),
                test_command=['cargo', 'test'],
                patterns=['tests/', 'src/**/tests.rs']
            )
        
        return None
    
    def _detect_dotnet(self) -> Optional[FrameworkInfo]:
        """Detect .NET testing"""
        # Look for *.csproj files
        csproj_files = list(self.root.glob('*.csproj'))
        if csproj_files:
            return FrameworkInfo(
                name='dotnet',
                config_file=str(csproj_files[0]),
                test_command=['dotnet', 'test'],
                patterns=['*Tests.cs', '*Test.cs']
            )
        
        return None
    
    def get_test_files(self) -> List[str]:
        """
        Get list of test files in the project.
        
        Returns:
            List of test file paths
        """
        framework = self.detect()
        
        if not framework:
            return []
        
        test_files = []
        
        for pattern in framework.patterns:
            if pattern.endswith('/'):
                # Directory pattern
                dir_path = self.root / pattern.rstrip('/')
                if dir_path.is_dir():
                    for f in dir_path.rglob('*'):
                        if f.is_file() and not f.name.startswith('.'):
                            test_files.append(str(f.relative_to(self.root)))
            else:
                # File pattern
                for f in self.root.rglob(pattern):
                    if f.is_file():
                        test_files.append(str(f.relative_to(self.root)))
        
        return sorted(set(test_files))


def detect_framework(root: str = None) -> Optional[FrameworkInfo]:
    """
    Convenience function to detect test framework.
    
    Args:
        root: Project root directory
        
    Returns:
        FrameworkInfo if detected
    """
    detector = TestDetector(root)
    return detector.detect()
