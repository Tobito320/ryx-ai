"""
Project Manifest System for Ryx.

Defines project metadata, test commands, lint configs, and build settings.
Supports auto-detection and manual configuration.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import tomllib


@dataclass
class ManifestConfig:
    """Project manifest configuration."""
    # Project info
    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    
    # Language/Framework
    language: str = ""  # python, javascript, typescript, go, rust
    framework: Optional[str] = None  # django, flask, react, vue, etc.
    
    # Commands
    test_command: Optional[str] = None
    lint_command: Optional[str] = None
    build_command: Optional[str] = None
    run_command: Optional[str] = None
    
    # Paths
    source_dirs: List[str] = field(default_factory=lambda: ["src", "lib"])
    test_dirs: List[str] = field(default_factory=lambda: ["tests", "test", "__tests__"])
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "node_modules", "venv", ".venv", "__pycache__", 
        ".git", "dist", "build", ".next", "target"
    ])
    
    # Important files
    entry_points: List[str] = field(default_factory=list)  # main.py, index.js, etc.
    config_files: List[str] = field(default_factory=list)  # pyproject.toml, package.json
    
    # Ryx-specific
    priority_files: List[str] = field(default_factory=list)  # Files to always include in context
    context_limit: int = 50  # Max files to include in context
    
    # Metadata
    detected: bool = False  # Whether this was auto-detected
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "language": self.language,
            "framework": self.framework,
            "commands": {
                "test": self.test_command,
                "lint": self.lint_command,
                "build": self.build_command,
                "run": self.run_command,
            },
            "paths": {
                "source": self.source_dirs,
                "test": self.test_dirs,
                "ignore": self.ignore_patterns,
            },
            "entry_points": self.entry_points,
            "priority_files": self.priority_files,
            "context_limit": self.context_limit,
            "custom": self.custom,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ManifestConfig':
        """Create from dictionary."""
        commands = data.get("commands", {})
        paths = data.get("paths", {})
        
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            language=data.get("language", ""),
            framework=data.get("framework"),
            test_command=commands.get("test"),
            lint_command=commands.get("lint"),
            build_command=commands.get("build"),
            run_command=commands.get("run"),
            source_dirs=paths.get("source", ["src", "lib"]),
            test_dirs=paths.get("test", ["tests", "test"]),
            ignore_patterns=paths.get("ignore", []),
            entry_points=data.get("entry_points", []),
            priority_files=data.get("priority_files", []),
            context_limit=data.get("context_limit", 50),
            custom=data.get("custom", {}),
        )


class ManifestLoader:
    """
    Loads and manages project manifests.
    
    Supports:
    - .ryx.json (Ryx-specific manifest)
    - pyproject.toml [tool.ryx] section
    - package.json ryx field
    - Auto-detection from project structure
    
    Usage:
        loader = ManifestLoader()
        manifest = loader.load()
        print(manifest.test_command)
    """
    
    MANIFEST_FILES = [
        '.ryx.json',
        '.ryx.yaml',
        'ryx.json',
    ]
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or os.getcwd())
        self._manifest: Optional[ManifestConfig] = None
    
    def load(self, force_detect: bool = False) -> ManifestConfig:
        """
        Load project manifest.
        
        Args:
            force_detect: Force auto-detection even if manifest exists
            
        Returns:
            ManifestConfig with project settings
        """
        if self._manifest and not force_detect:
            return self._manifest
        
        # Try loading from manifest files
        manifest = self._load_from_file()
        
        if not manifest or force_detect:
            # Auto-detect
            manifest = self._detect_project()
        
        self._manifest = manifest
        return manifest
    
    def save(self, manifest: Optional[ManifestConfig] = None):
        """Save manifest to .ryx.json."""
        manifest = manifest or self._manifest
        if not manifest:
            return
        
        path = self.root_path / '.ryx.json'
        with open(path, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)
    
    def _load_from_file(self) -> Optional[ManifestConfig]:
        """Try loading from manifest files."""
        # Check .ryx.json
        for fname in self.MANIFEST_FILES:
            path = self.root_path / fname
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    return ManifestConfig.from_dict(data)
                except Exception:
                    pass
        
        # Check pyproject.toml [tool.ryx]
        pyproject = self.root_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                with open(pyproject, 'rb') as f:
                    data = tomllib.load(f)
                if 'tool' in data and 'ryx' in data['tool']:
                    return ManifestConfig.from_dict(data['tool']['ryx'])
            except Exception:
                pass
        
        # Check package.json ryx field
        package_json = self.root_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                if 'ryx' in data:
                    return ManifestConfig.from_dict(data['ryx'])
            except Exception:
                pass
        
        return None
    
    def _detect_project(self) -> ManifestConfig:
        """Auto-detect project configuration."""
        manifest = ManifestConfig(detected=True)
        
        # Detect language and framework
        self._detect_language(manifest)
        
        # Detect commands
        self._detect_commands(manifest)
        
        # Detect entry points
        self._detect_entry_points(manifest)
        
        # Detect important config files
        self._detect_config_files(manifest)
        
        return manifest
    
    def _detect_language(self, manifest: ManifestConfig):
        """Detect primary language."""
        # Check for language-specific files
        indicators = {
            'python': ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile'],
            'javascript': ['package.json'],
            'typescript': ['tsconfig.json'],
            'go': ['go.mod'],
            'rust': ['Cargo.toml'],
            'java': ['pom.xml', 'build.gradle'],
        }
        
        for lang, files in indicators.items():
            for f in files:
                if (self.root_path / f).exists():
                    manifest.language = lang
                    break
            if manifest.language:
                break
        
        # Detect framework
        if manifest.language == 'python':
            if (self.root_path / 'manage.py').exists():
                manifest.framework = 'django'
            elif any((self.root_path / f).exists() for f in ['app.py', 'wsgi.py']):
                manifest.framework = 'flask'
            elif (self.root_path / 'main.py').exists():
                manifest.framework = 'fastapi'  # common pattern
        
        elif manifest.language in ['javascript', 'typescript']:
            package_json = self.root_path / 'package.json'
            if package_json.exists():
                try:
                    with open(package_json) as f:
                        data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    if 'react' in deps:
                        manifest.framework = 'react'
                    elif 'vue' in deps:
                        manifest.framework = 'vue'
                    elif 'next' in deps:
                        manifest.framework = 'nextjs'
                    elif '@angular/core' in deps:
                        manifest.framework = 'angular'
                except Exception:
                    pass
    
    def _detect_commands(self, manifest: ManifestConfig):
        """Detect test/lint/build commands."""
        # Python
        if manifest.language == 'python':
            # Test command
            if (self.root_path / 'pytest.ini').exists() or \
               (self.root_path / 'pyproject.toml').exists():
                manifest.test_command = 'pytest'
            elif (self.root_path / 'tests').exists():
                manifest.test_command = 'python -m pytest'
            
            # Lint command
            if (self.root_path / 'ruff.toml').exists():
                manifest.lint_command = 'ruff check .'
            elif (self.root_path / '.flake8').exists():
                manifest.lint_command = 'flake8'
            else:
                manifest.lint_command = 'ruff check .'  # default
        
        # JavaScript/TypeScript
        elif manifest.language in ['javascript', 'typescript']:
            package_json = self.root_path / 'package.json'
            if package_json.exists():
                try:
                    with open(package_json) as f:
                        data = json.load(f)
                    scripts = data.get('scripts', {})
                    if 'test' in scripts:
                        manifest.test_command = 'npm test'
                    if 'lint' in scripts:
                        manifest.lint_command = 'npm run lint'
                    if 'build' in scripts:
                        manifest.build_command = 'npm run build'
                except Exception:
                    pass
        
        # Go
        elif manifest.language == 'go':
            manifest.test_command = 'go test ./...'
            manifest.lint_command = 'golangci-lint run'
            manifest.build_command = 'go build'
        
        # Rust
        elif manifest.language == 'rust':
            manifest.test_command = 'cargo test'
            manifest.lint_command = 'cargo clippy'
            manifest.build_command = 'cargo build'
    
    def _detect_entry_points(self, manifest: ManifestConfig):
        """Detect main entry point files."""
        common_entries = [
            'main.py', 'app.py', '__main__.py',
            'index.js', 'index.ts', 'main.js', 'main.ts',
            'src/main.py', 'src/index.js', 'src/index.ts',
            'main.go', 'cmd/main.go',
            'src/main.rs', 'src/lib.rs',
        ]
        
        for entry in common_entries:
            if (self.root_path / entry).exists():
                manifest.entry_points.append(entry)
    
    def _detect_config_files(self, manifest: ManifestConfig):
        """Detect important config files."""
        config_patterns = [
            'pyproject.toml', 'setup.py', 'setup.cfg',
            'package.json', 'tsconfig.json',
            'go.mod', 'Cargo.toml',
            '.env', '.env.example',
            'Dockerfile', 'docker-compose.yml',
            'Makefile', 'justfile',
            '.github/workflows/*.yml',
        ]
        
        for pattern in config_patterns:
            if '*' in pattern:
                # Glob pattern
                for f in self.root_path.glob(pattern):
                    manifest.config_files.append(str(f.relative_to(self.root_path)))
            elif (self.root_path / pattern).exists():
                manifest.config_files.append(pattern)
    
    def get_test_command(self) -> Optional[str]:
        """Get test command."""
        manifest = self.load()
        return manifest.test_command
    
    def get_lint_command(self) -> Optional[str]:
        """Get lint command."""
        manifest = self.load()
        return manifest.lint_command
    
    def get_ignore_patterns(self) -> List[str]:
        """Get ignore patterns."""
        manifest = self.load()
        return manifest.ignore_patterns
    
    def get_priority_files(self) -> List[str]:
        """Get priority files for context."""
        manifest = self.load()
        return manifest.priority_files + manifest.entry_points + manifest.config_files[:5]


# Convenience functions
def load_manifest(path: Optional[str] = None) -> ManifestConfig:
    """Quick load manifest."""
    return ManifestLoader(path).load()

def detect_project(path: Optional[str] = None) -> ManifestConfig:
    """Quick detect project settings."""
    return ManifestLoader(path).load(force_detect=True)
