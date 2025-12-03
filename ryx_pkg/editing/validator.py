"""
Ryx Edit Validator

Validates edits before applying them.
Ensures safety and correctness of code modifications.
"""

import os
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A validation issue"""
    level: str  # 'error', 'warning', 'info'
    message: str
    line: Optional[int] = None
    file: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of edit validation"""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(self, message: str, line: int = None, file: str = None):
        self.issues.append(ValidationIssue('error', message, line, file))
        self.valid = False
    
    def add_warning(self, message: str, line: int = None, file: str = None):
        self.issues.append(ValidationIssue('warning', message, line, file))
    
    def add_info(self, message: str, line: int = None, file: str = None):
        self.issues.append(ValidationIssue('info', message, line, file))
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'error']
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'warning']


class EditValidator:
    """
    Validates code edits before applying.
    
    Checks:
    - Syntax validity (for supported languages)
    - File existence and permissions
    - Dangerous patterns
    - Size limits
    """
    
    # Dangerous patterns to warn about
    DANGEROUS_PATTERNS = [
        (r'rm\s+-rf?\s+/', "Dangerous rm command"),
        (r'eval\s*\(', "Use of eval()"),
        (r'exec\s*\(', "Use of exec()"),
        (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell injection risk"),
        (r'os\.system\s*\(', "Use of os.system()"),
        (r'__import__\s*\(', "Dynamic import"),
    ]
    
    # Maximum file size to edit (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    def __init__(self, root: str = None, strict: bool = False):
        """
        Initialize EditValidator.
        
        Args:
            root: Root directory for relative paths
            strict: Fail on warnings too
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.strict = strict
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate that a file can be edited.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        # Resolve path
        if not os.path.isabs(file_path):
            full_path = self.root / file_path
        else:
            full_path = Path(file_path)
        
        # Check existence
        if not full_path.exists():
            result.add_warning(f"File does not exist: {file_path}", file=file_path)
            return result
        
        # Check if it's a file
        if not full_path.is_file():
            result.add_error(f"Not a file: {file_path}", file=file_path)
            return result
        
        # Check permissions
        if not os.access(full_path, os.W_OK):
            result.add_error(f"No write permission: {file_path}", file=file_path)
            return result
        
        # Check size
        size = full_path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            result.add_error(
                f"File too large: {size / 1024 / 1024:.1f}MB (max {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)",
                file=file_path
            )
            return result
        
        return result
    
    def validate_content(
        self,
        content: str,
        file_path: str = None
    ) -> ValidationResult:
        """
        Validate content to be written.
        
        Args:
            content: Content to validate
            file_path: Optional file path for context
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        # Check for dangerous patterns
        for pattern, message in self.DANGEROUS_PATTERNS:
            matches = list(re.finditer(pattern, content))
            for match in matches:
                line = content[:match.start()].count('\n') + 1
                result.add_warning(f"{message} at line {line}", line=line, file=file_path)
        
        # Validate syntax if we can determine the language
        if file_path:
            ext = Path(file_path).suffix.lower()
            
            if ext == '.py':
                syntax_result = self._validate_python_syntax(content)
                if syntax_result:
                    result.add_error(
                        f"Python syntax error: {syntax_result}",
                        file=file_path
                    )
            
            elif ext in ('.json',):
                syntax_result = self._validate_json_syntax(content)
                if syntax_result:
                    result.add_error(
                        f"JSON syntax error: {syntax_result}",
                        file=file_path
                    )
        
        # Check for very long lines
        for i, line in enumerate(content.split('\n'), 1):
            if len(line) > 500:
                result.add_warning(
                    f"Very long line ({len(line)} chars)",
                    line=i,
                    file=file_path
                )
        
        if self.strict and result.warnings:
            result.valid = False
        
        return result
    
    def validate_diff(
        self,
        diff_text: str,
        file_path: str = None
    ) -> ValidationResult:
        """
        Validate a diff before applying.
        
        Args:
            diff_text: Unified diff text
            file_path: Target file path
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        # Check for valid diff format
        has_hunks = bool(re.search(r'^@@\s+-\d+', diff_text, re.MULTILINE))
        
        if not has_hunks:
            result.add_error("No valid diff hunks found")
            return result
        
        # Count additions/deletions
        additions = len(re.findall(r'^\+[^+]', diff_text, re.MULTILINE))
        deletions = len(re.findall(r'^-[^-]', diff_text, re.MULTILINE))
        
        if additions == 0 and deletions == 0:
            result.add_warning("Diff has no actual changes")
        
        # Check for very large diffs
        if additions + deletions > 1000:
            result.add_warning(f"Large diff: {additions} additions, {deletions} deletions")
        
        # Validate file if specified
        if file_path:
            file_result = self.validate_file(file_path)
            result.issues.extend(file_result.issues)
            if not file_result.valid:
                result.valid = False
        
        return result
    
    def _validate_python_syntax(self, content: str) -> Optional[str]:
        """Check Python syntax"""
        try:
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"line {e.lineno}: {e.msg}"
    
    def _validate_json_syntax(self, content: str) -> Optional[str]:
        """Check JSON syntax"""
        import json
        try:
            json.loads(content)
            return None
        except json.JSONDecodeError as e:
            return f"line {e.lineno}: {e.msg}"
    
    def validate_edit(
        self,
        file_path: str,
        new_content: str = None,
        diff_text: str = None
    ) -> ValidationResult:
        """
        Comprehensive edit validation.
        
        Args:
            file_path: File to edit
            new_content: New content (for full replacement)
            diff_text: Diff text (for patch)
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        # Validate file
        file_result = self.validate_file(file_path)
        result.issues.extend(file_result.issues)
        if not file_result.valid:
            result.valid = False
            return result
        
        # Validate content or diff
        if new_content:
            content_result = self.validate_content(new_content, file_path)
            result.issues.extend(content_result.issues)
            if not content_result.valid:
                result.valid = False
        
        if diff_text:
            diff_result = self.validate_diff(diff_text, file_path)
            result.issues.extend(diff_result.issues)
            if not diff_result.valid:
                result.valid = False
        
        return result
