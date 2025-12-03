"""
Error Classification and Recovery for Ryx.

Classifies errors into types and provides recovery strategies.
Inspired by Claude Code's error handling patterns.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
import re
import traceback


class ErrorType(Enum):
    """Classification of error types."""
    SYNTAX_ERROR = auto()       # Python/JS syntax errors
    FILE_NOT_FOUND = auto()     # Missing files
    PERMISSION_DENIED = auto()  # File/command permissions
    IMPORT_ERROR = auto()       # Missing packages/modules
    TEST_FAILURE = auto()       # Test assertions failed
    LINT_ERROR = auto()         # Linting/formatting issues
    GIT_ERROR = auto()          # Git operation failures
    TIMEOUT = auto()            # Command/operation timeout
    NETWORK_ERROR = auto()      # Network/API failures
    LLM_ERROR = auto()          # LLM response issues
    TOOL_ERROR = auto()         # Tool execution failure
    UNKNOWN = auto()            # Unclassified errors


@dataclass
class ErrorContext:
    """Context about an error for recovery."""
    error_type: ErrorType
    message: str
    original_exception: Optional[Exception] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    can_auto_recover: bool = False
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def can_retry(self) -> bool:
        return self.recovery_attempts < self.max_recovery_attempts
    
    def to_llm_context(self) -> str:
        """Format error for LLM understanding."""
        lines = [
            f"Error Type: {self.error_type.name}",
            f"Message: {self.message}",
        ]
        if self.file_path:
            lines.append(f"File: {self.file_path}")
        if self.line_number:
            lines.append(f"Line: {self.line_number}")
        if self.code_snippet:
            lines.append(f"Code:\n```\n{self.code_snippet}\n```")
        if self.suggested_fix:
            lines.append(f"Suggested Fix: {self.suggested_fix}")
        return "\n".join(lines)


class ErrorClassifier:
    """
    Classifies errors into types for appropriate handling.
    
    Usage:
        classifier = ErrorClassifier()
        context = classifier.classify(exception)
        if context.error_type == ErrorType.SYNTAX_ERROR:
            # handle syntax error
    """
    
    # Patterns for error classification
    PATTERNS = {
        ErrorType.SYNTAX_ERROR: [
            r'SyntaxError:',
            r'IndentationError:',
            r'TabError:',
            r'invalid syntax',
            r'unexpected token',
            r'Parsing error',
        ],
        ErrorType.FILE_NOT_FOUND: [
            r'FileNotFoundError:',
            r'No such file or directory',
            r'ENOENT',
            r'path does not exist',
            r'file not found',
        ],
        ErrorType.PERMISSION_DENIED: [
            r'PermissionError:',
            r'Permission denied',
            r'EACCES',
            r'Operation not permitted',
        ],
        ErrorType.IMPORT_ERROR: [
            r'ModuleNotFoundError:',
            r'ImportError:',
            r'No module named',
            r'cannot import name',
        ],
        ErrorType.TEST_FAILURE: [
            r'AssertionError:',
            r'FAILED',
            r'test.*failed',
            r'pytest.*error',
            r'npm test.*fail',
        ],
        ErrorType.LINT_ERROR: [
            r'flake8',
            r'pylint',
            r'ruff',
            r'eslint',
            r'prettier',
            r'E\d{3}:',  # PEP8 error codes
            r'W\d{3}:',  # PEP8 warning codes
        ],
        ErrorType.GIT_ERROR: [
            r'fatal:.*git',
            r'git.*error',
            r'merge conflict',
            r'not a git repository',
            r'checkout.*failed',
        ],
        ErrorType.TIMEOUT: [
            r'TimeoutError:',
            r'timed out',
            r'timeout expired',
            r'deadline exceeded',
        ],
        ErrorType.NETWORK_ERROR: [
            r'ConnectionError:',
            r'ConnectionRefusedError:',
            r'Network.*unreachable',
            r'ECONNREFUSED',
            r'socket.*error',
        ],
        ErrorType.LLM_ERROR: [
            r'ollama.*error',
            r'model.*not found',
            r'context length exceeded',
            r'rate limit',
            r'API.*error',
        ],
    }
    
    # Recovery strategies per error type
    RECOVERY_STRATEGIES = {
        ErrorType.SYNTAX_ERROR: "Review the syntax error, fix the specific line mentioned, and try again.",
        ErrorType.FILE_NOT_FOUND: "Check if the file path is correct. Use find_relevant_files to locate the right file.",
        ErrorType.PERMISSION_DENIED: "Check file permissions or try a different approach that doesn't require these permissions.",
        ErrorType.IMPORT_ERROR: "Install the missing package with pip or verify the import path is correct.",
        ErrorType.TEST_FAILURE: "Review the failing test, understand the assertion, and fix the implementation.",
        ErrorType.LINT_ERROR: "Fix the linting issues in the code - they're usually formatting or style problems.",
        ErrorType.GIT_ERROR: "Check git status and resolve any conflicts or uncommitted changes first.",
        ErrorType.TIMEOUT: "Simplify the operation or break it into smaller steps.",
        ErrorType.NETWORK_ERROR: "Check network connectivity. If using external APIs, verify they're accessible.",
        ErrorType.LLM_ERROR: "Retry with a simpler prompt or check if the model is running correctly.",
        ErrorType.TOOL_ERROR: "Review the tool parameters and try again with corrected inputs.",
        ErrorType.UNKNOWN: "Analyze the error message carefully and attempt a targeted fix.",
    }
    
    def classify(self, error: Exception) -> ErrorContext:
        """
        Classify an exception into an ErrorContext.
        
        Args:
            error: The exception to classify
            
        Returns:
            ErrorContext with classification and recovery info
        """
        error_str = str(error)
        tb_str = traceback.format_exception(type(error), error, error.__traceback__)
        full_error = ''.join(tb_str)
        
        # Determine error type
        error_type = self._match_error_type(error_str + full_error)
        
        # Extract details
        file_path, line_number = self._extract_location(full_error)
        code_snippet = self._extract_code_snippet(full_error)
        
        return ErrorContext(
            error_type=error_type,
            message=error_str,
            original_exception=error,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            suggested_fix=self.RECOVERY_STRATEGIES.get(error_type, self.RECOVERY_STRATEGIES[ErrorType.UNKNOWN]),
            can_auto_recover=error_type in {ErrorType.SYNTAX_ERROR, ErrorType.LINT_ERROR, ErrorType.IMPORT_ERROR},
        )
    
    def classify_from_output(self, output: str) -> ErrorContext:
        """Classify from command output string."""
        error_type = self._match_error_type(output)
        file_path, line_number = self._extract_location(output)
        
        return ErrorContext(
            error_type=error_type,
            message=output[:500],  # First 500 chars
            file_path=file_path,
            line_number=line_number,
            suggested_fix=self.RECOVERY_STRATEGIES.get(error_type, self.RECOVERY_STRATEGIES[ErrorType.UNKNOWN]),
            can_auto_recover=error_type in {ErrorType.SYNTAX_ERROR, ErrorType.LINT_ERROR},
        )
    
    def _match_error_type(self, text: str) -> ErrorType:
        """Match text against error patterns."""
        text_lower = text.lower()
        
        for error_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return error_type
        
        return ErrorType.UNKNOWN
    
    def _extract_location(self, text: str) -> tuple:
        """Extract file path and line number from error text."""
        # Pattern: File "path", line N
        match = re.search(r'File ["\']([^"\']+)["\'],\s*line\s*(\d+)', text)
        if match:
            return match.group(1), int(match.group(2))
        
        # Pattern: at path:line
        match = re.search(r'at\s+([^\s:]+):(\d+)', text)
        if match:
            return match.group(1), int(match.group(2))
        
        # Pattern: path:line:col
        match = re.search(r'^([^\s:]+):(\d+):\d+', text, re.MULTILINE)
        if match:
            return match.group(1), int(match.group(2))
        
        return None, None
    
    def _extract_code_snippet(self, text: str) -> Optional[str]:
        """Extract code snippet from error traceback."""
        # Look for indented code lines after "line N"
        match = re.search(r'line\s+\d+.*?\n(\s{4,}.+)', text)
        if match:
            return match.group(1).strip()
        return None


class ErrorRecoveryLoop:
    """
    Manages error recovery with retry logic.
    
    Usage:
        loop = ErrorRecoveryLoop()
        
        @loop.with_recovery
        async def risky_operation():
            # code that might fail
            pass
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.classifier = ErrorClassifier()
        self.error_history: List[ErrorContext] = []
    
    def attempt(self, operation: Callable, *args, **kwargs) -> tuple:
        """
        Attempt an operation with recovery.
        
        Returns:
            (success: bool, result_or_error: Any)
        """
        for attempt in range(self.max_retries):
            try:
                result = operation(*args, **kwargs)
                return True, result
            except Exception as e:
                context = self.classifier.classify(e)
                context.recovery_attempts = attempt + 1
                self.error_history.append(context)
                
                if not context.can_retry:
                    return False, context
                
                # Log for debugging
                print(f"⚠️ Attempt {attempt + 1}/{self.max_retries} failed: {context.error_type.name}")
        
        return False, self.error_history[-1] if self.error_history else None
    
    def get_recovery_context(self) -> str:
        """Get accumulated error context for LLM."""
        if not self.error_history:
            return ""
        
        lines = ["Previous errors encountered:"]
        for i, ctx in enumerate(self.error_history[-3:], 1):  # Last 3 errors
            lines.append(f"\nAttempt {i}:")
            lines.append(ctx.to_llm_context())
        
        return "\n".join(lines)
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()


# Convenience functions
def classify_error(error: Exception) -> ErrorContext:
    """Quick classify an exception."""
    return ErrorClassifier().classify(error)

def classify_output(output: str) -> ErrorContext:
    """Quick classify from output string."""
    return ErrorClassifier().classify_from_output(output)
