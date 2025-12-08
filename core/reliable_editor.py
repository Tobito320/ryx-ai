"""
Ryx AI - Reliable Editor (Extracted from Aider patterns)

The #1 problem with LLM coding agents is edit reliability.
This module implements multiple strategies to ensure edits succeed:

1. Exact match (fastest)
2. Fuzzy match with SequenceMatcher
3. Whitespace-flexible matching (LLM often messes up indentation)
4. Line-by-line diff patching
5. Backup & recovery

Key insight from Aider: Try multiple strategies in order of precision.
If one fails, try the next. Only fail if ALL strategies fail.
"""

import os
import re
import shutil
import difflib
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from core.paths import get_data_dir


@dataclass
class EditResult:
    """Result of an edit operation"""
    success: bool
    message: str
    strategy_used: Optional[str] = None
    backup_path: Optional[str] = None
    diff: Optional[str] = None
    
    
class ReliableEditor:
    """
    Reliable file editor with multiple fallback strategies.
    
    Philosophy: The LLM is imperfect. The editor should compensate.
    
    Strategies (in order):
    1. exact_match - Search text matches file exactly
    2. whitespace_flex - Ignore leading whitespace differences
    3. fuzzy_match - Use SequenceMatcher to find similar regions
    4. line_anchor - Find by surrounding lines context
    5. content_only - Match non-whitespace content only
    
    Always:
    - Create backup before modifying
    - Validate syntax after edit (for code files)
    - Show diff to user
    """
    
    BACKUP_DIR = ".ryx.backups"
    SIMILARITY_THRESHOLD = 0.6  # Minimum similarity for fuzzy match
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / self.BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)
        
    def edit(
        self,
        file_path: str,
        search_text: str,
        replace_text: str,
        create_if_missing: bool = True,
        validate_syntax: bool = True
    ) -> EditResult:
        """
        Edit a file with reliable multi-strategy matching.
        
        Args:
            file_path: Path to the file (relative or absolute)
            search_text: Text to find and replace
            replace_text: Text to replace with
            create_if_missing: Create file if it doesn't exist
            validate_syntax: Check syntax after edit (Python only for now)
            
        Returns:
            EditResult with success status and details
        """
        # Resolve path
        path = self._resolve_path(file_path)
        
        # Handle literal escape sequences from LLM
        search_text = self._unescape_text(search_text)
        replace_text = self._unescape_text(replace_text)
        
        # Handle new file creation
        if not path.exists():
            if create_if_missing and not search_text.strip():
                return self._create_file(path, replace_text)
            return EditResult(False, f"File not found: {file_path}")
        
        # Read current content
        try:
            content = path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            return EditResult(False, f"Failed to read file: {e}")
        
        # Try empty search = append mode
        if not search_text.strip():
            return self._append_to_file(path, content, replace_text)
        
        # Create backup
        backup_path = self._create_backup(path, content)
        
        # Try each strategy in order
        strategies = [
            ('exact_match', self._exact_match),
            ('whitespace_flex', self._whitespace_flex_match),
            ('fuzzy_match', self._fuzzy_match),
            ('line_anchor', self._line_anchor_match),
            ('content_only', self._content_only_match),
        ]
        
        for strategy_name, strategy_fn in strategies:
            new_content = strategy_fn(content, search_text, replace_text)
            if new_content is not None:
                # Validate if requested
                if validate_syntax and path.suffix == '.py':
                    syntax_ok, error = self._validate_python_syntax(new_content)
                    if not syntax_ok:
                        continue  # Try next strategy
                
                # Write the edited content
                try:
                    path.write_text(new_content, encoding='utf-8')
                    diff = self._generate_diff(content, new_content, str(path))
                    return EditResult(
                        success=True,
                        message=f"Edit applied using {strategy_name}",
                        strategy_used=strategy_name,
                        backup_path=str(backup_path),
                        diff=diff
                    )
                except Exception as e:
                    return EditResult(False, f"Failed to write file: {e}")
        
        # All strategies failed - provide helpful feedback
        similar_lines = self._find_similar_lines(content, search_text)
        hint = ""
        if similar_lines:
            hint = f"\n\nDid you mean:\n```\n{similar_lines}\n```"
            
        return EditResult(
            False,
            f"Could not find matching text in {file_path}.{hint}",
            backup_path=str(backup_path)
        )
    
    def _unescape_text(self, text: str) -> str:
        """Handle literal escape sequences from LLM output"""
        # Replace literal \n with actual newlines
        text = text.replace('\\n', '\n')
        # Replace literal \t with tabs
        text = text.replace('\\t', '\t')
        return text
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to project root"""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()
    
    def _create_backup(self, path: Path, content: str) -> Path:
        """Create timestamped backup of file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rel_path = path.relative_to(self.project_root) if path.is_relative_to(self.project_root) else path
        backup_name = f"{rel_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        backup_path.write_text(content, encoding='utf-8')
        return backup_path
    
    def _create_file(self, path: Path, content: str) -> EditResult:
        """Create a new file"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return EditResult(True, f"Created new file: {path}")
        except Exception as e:
            return EditResult(False, f"Failed to create file: {e}")
    
    def _append_to_file(self, path: Path, content: str, new_text: str) -> EditResult:
        """Append text to file"""
        backup_path = self._create_backup(path, content)
        new_content = content + new_text
        try:
            path.write_text(new_content, encoding='utf-8')
            return EditResult(
                True, 
                f"Appended to {path}",
                strategy_used='append',
                backup_path=str(backup_path)
            )
        except Exception as e:
            return EditResult(False, f"Failed to append: {e}")
    
    # === MATCHING STRATEGIES ===
    
    def _exact_match(self, content: str, search: str, replace: str) -> Optional[str]:
        """Strategy 1: Exact string match"""
        if search in content:
            # Ensure it's unique
            if content.count(search) == 1:
                return content.replace(search, replace)
            # Multiple matches - still try if user is precise
            return content.replace(search, replace, 1)
        return None
    
    def _whitespace_flex_match(self, content: str, search: str, replace: str) -> Optional[str]:
        """Strategy 2: Flexible leading whitespace matching (LLM often gets indentation wrong)"""
        content_lines = content.splitlines(keepends=True)
        search_lines = search.splitlines(keepends=True)
        replace_lines = replace.splitlines(keepends=True)
        
        if not search_lines:
            return None
            
        # Normalize: strip leading whitespace for comparison
        search_stripped = [line.lstrip() for line in search_lines]
        
        for i in range(len(content_lines) - len(search_lines) + 1):
            chunk = content_lines[i:i + len(search_lines)]
            chunk_stripped = [line.lstrip() for line in chunk]
            
            if chunk_stripped == search_stripped:
                # Found match! Determine the indentation to add
                if chunk[0].strip():  # Non-empty first line
                    indent = chunk[0][:len(chunk[0]) - len(chunk[0].lstrip())]
                else:
                    indent = ""
                
                # Apply same indentation to replacement
                indented_replace = []
                for j, line in enumerate(replace_lines):
                    if line.strip():  # Non-empty line
                        # Preserve relative indentation from replacement
                        if j < len(search_lines) and search_lines[j].strip():
                            orig_indent = len(search_lines[j]) - len(search_lines[j].lstrip())
                            new_indent = len(line) - len(line.lstrip())
                            extra_indent = max(0, new_indent - orig_indent)
                            indented_replace.append(indent + ' ' * extra_indent + line.lstrip())
                        else:
                            indented_replace.append(indent + line.lstrip())
                    else:
                        indented_replace.append(line)
                
                result = content_lines[:i] + indented_replace + content_lines[i + len(search_lines):]
                return ''.join(result)
        
        return None
    
    def _fuzzy_match(self, content: str, search: str, replace: str) -> Optional[str]:
        """Strategy 3: Fuzzy matching with SequenceMatcher"""
        content_lines = content.splitlines(keepends=True)
        search_lines = search.splitlines(keepends=True)
        
        if not search_lines:
            return None
        
        best_ratio = 0
        best_start = -1
        best_end = -1
        
        # Try different chunk sizes around the search length
        for length in range(len(search_lines) - 2, len(search_lines) + 3):
            if length <= 0 or length > len(content_lines):
                continue
                
            for i in range(len(content_lines) - length + 1):
                chunk = ''.join(content_lines[i:i + length])
                ratio = SequenceMatcher(None, chunk, search).ratio()
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_start = i
                    best_end = i + length
        
        if best_ratio >= self.SIMILARITY_THRESHOLD:
            result = content_lines[:best_start] + [replace] + content_lines[best_end:]
            # Ensure replace ends with newline if original chunk did
            return ''.join(result)
        
        return None
    
    def _line_anchor_match(self, content: str, search: str, replace: str) -> Optional[str]:
        """Strategy 4: Find by anchor lines (first and last lines of search)"""
        content_lines = content.splitlines()
        search_lines = search.strip().splitlines()
        
        if len(search_lines) < 2:
            return None
        
        first_line = search_lines[0].strip()
        last_line = search_lines[-1].strip()
        
        # Find all occurrences of first line
        starts = [i for i, line in enumerate(content_lines) if line.strip() == first_line]
        
        for start in starts:
            # Look for matching last line
            expected_end = start + len(search_lines) - 1
            if expected_end < len(content_lines):
                if content_lines[expected_end].strip() == last_line:
                    # Found matching anchors - replace the block
                    result_lines = content_lines[:start] + replace.splitlines() + content_lines[expected_end + 1:]
                    return '\n'.join(result_lines) + '\n'
        
        return None
    
    def _content_only_match(self, content: str, search: str, replace: str) -> Optional[str]:
        """Strategy 5: Match by non-whitespace content only"""
        # Remove all whitespace for comparison
        content_compact = re.sub(r'\s+', '', content)
        search_compact = re.sub(r'\s+', '', search)
        
        if search_compact not in content_compact:
            return None
        
        # Found in compacted form - now find actual location
        # This is expensive but a last resort
        content_lines = content.splitlines(keepends=True)
        search_lines = search.splitlines()
        
        for i in range(len(content_lines)):
            chunk_lines = []
            j = i
            while j < len(content_lines) and len(chunk_lines) < len(search_lines) * 2:
                chunk_lines.append(content_lines[j])
                j += 1
                
                chunk_compact = re.sub(r'\s+', '', ''.join(chunk_lines))
                if search_compact in chunk_compact:
                    # Found it - replace this chunk
                    result = content_lines[:i] + [replace] + content_lines[j:]
                    return ''.join(result)
        
        return None
    
    # === HELPERS ===
    
    def _find_similar_lines(self, content: str, search: str, threshold: float = 0.6) -> str:
        """Find lines similar to the search text (for error hints)"""
        search_lines = search.strip().splitlines()
        content_lines = content.splitlines()
        
        if not search_lines:
            return ""
        
        best_ratio = 0
        best_chunk = []
        
        for i in range(len(content_lines) - len(search_lines) + 1):
            chunk = content_lines[i:i + len(search_lines)]
            ratio = SequenceMatcher(None, search_lines, chunk).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_chunk = chunk
        
        if best_ratio >= threshold:
            return '\n'.join(best_chunk)
        return ""
    
    def _validate_python_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax"""
        try:
            compile(content, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, str(e)
    
    def _generate_diff(self, old: str, new: str, filename: str) -> str:
        """Generate unified diff"""
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        )
        return ''.join(diff)
    
    def restore_backup(self, file_path: str, backup_path: str) -> EditResult:
        """Restore file from backup"""
        try:
            backup = Path(backup_path)
            target = self._resolve_path(file_path)
            
            if not backup.exists():
                return EditResult(False, f"Backup not found: {backup_path}")
            
            shutil.copy2(backup, target)
            return EditResult(True, f"Restored {file_path} from backup")
        except Exception as e:
            return EditResult(False, f"Restore failed: {e}")


# Global instance for convenience
_editor: Optional[ReliableEditor] = None


def get_editor(project_root: str = ".") -> ReliableEditor:
    """Get or create the global reliable editor"""
    global _editor
    if _editor is None:
        _editor = ReliableEditor(project_root)
    return _editor


def reliable_edit(file_path: str, search: str, replace: str) -> EditResult:
    """Convenience function for quick edits"""
    return get_editor().edit(file_path, search, replace)


def append_method_to_class(file_path: str, class_name: str, method_code: str) -> EditResult:
    """
    Append a method to a class - bypasses LLM anchor finding.
    
    The method_code should be properly indented already (4 spaces for method, 8 for body).
    """
    from pathlib import Path
    import re
    
    path = Path(file_path)
    if not path.exists():
        return EditResult(False, f"File not found: {file_path}")
    
    content = path.read_text(encoding='utf-8', errors='replace')
    
    # Just append before the last line if it's a class file
    # Find the last non-empty, non-comment line
    lines = content.rstrip().split('\n')
    
    # The method code should already be properly indented
    # Just append at the end
    new_content = content.rstrip() + '\n\n' + method_code.rstrip() + '\n'
    
    # Write back
    path.write_text(new_content, encoding='utf-8')
    
    return EditResult(True, f"Appended method to end of file", strategy_used="append_to_class")
