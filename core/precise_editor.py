"""
Ryx Precise Code Editor

A surgical code modification system that:
1. Reads existing file content
2. Generates ONLY the specific changes needed (as search/replace pairs)
3. Applies changes precisely without touching other code
4. Validates changes before and after

This is designed to be MORE precise than Claude Code by:
- Never regenerating entire files
- Using search/replace for surgical edits
- Multiple validation passes
- Automatic rollback on any error
"""

import os
import re
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class EditType(Enum):
    INSERT_AFTER = "insert_after"      # Insert new code after a marker
    INSERT_BEFORE = "insert_before"    # Insert new code before a marker
    REPLACE = "replace"                # Replace exact text with new text
    APPEND = "append"                  # Append to end of file
    PREPEND = "prepend"                # Prepend to start of file


@dataclass
class CodeEdit:
    """A single surgical code edit"""
    edit_type: EditType
    search: str          # Text to find (for INSERT_AFTER/BEFORE/REPLACE)
    content: str         # New content to insert/replace with
    description: str = ""  # Human-readable description
    
    def __post_init__(self):
        # Normalize line endings
        self.search = self.search.replace('\r\n', '\n') if self.search else ""
        self.content = self.content.replace('\r\n', '\n')


@dataclass 
class EditResult:
    """Result of applying an edit"""
    success: bool
    message: str
    original_content: str = ""
    new_content: str = ""
    diff: str = ""


class PreciseCodeEditor:
    """
    Surgical code editor that makes minimal, precise changes.
    
    Key principles:
    1. NEVER regenerate entire files
    2. Find exact locations for changes
    3. Apply changes with minimal footprint
    4. Validate thoroughly
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.original_content = ""
        self.current_content = ""
        self.edits_applied: List[CodeEdit] = []
        self._load_file()
        
    def _load_file(self):
        """Load the file content"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
                self.current_content = self.original_content
        else:
            self.original_content = ""
            self.current_content = ""
            
    def apply_edit(self, edit: CodeEdit) -> EditResult:
        """Apply a single edit precisely"""
        before = self.current_content
        
        try:
            if edit.edit_type == EditType.REPLACE:
                result = self._apply_replace(edit)
            elif edit.edit_type == EditType.INSERT_AFTER:
                result = self._apply_insert_after(edit)
            elif edit.edit_type == EditType.INSERT_BEFORE:
                result = self._apply_insert_before(edit)
            elif edit.edit_type == EditType.APPEND:
                result = self._apply_append(edit)
            elif edit.edit_type == EditType.PREPEND:
                result = self._apply_prepend(edit)
            else:
                return EditResult(False, f"Unknown edit type: {edit.edit_type}")
                
            if result.success:
                self.edits_applied.append(edit)
                result.original_content = before
                result.new_content = self.current_content
                result.diff = self._generate_diff(before, self.current_content)
                
            return result
            
        except Exception as e:
            return EditResult(False, f"Edit failed: {str(e)}")
            
    def _apply_replace(self, edit: CodeEdit) -> EditResult:
        """Replace exact text"""
        if not edit.search:
            return EditResult(False, "Replace requires search text")
            
        # Count occurrences
        count = self.current_content.count(edit.search)
        
        if count == 0:
            # Try fuzzy match for common whitespace issues
            normalized_search = self._normalize_whitespace(edit.search)
            normalized_content = self._normalize_whitespace(self.current_content)
            
            if normalized_search in normalized_content:
                # Find the actual text with original whitespace
                actual = self._find_fuzzy_match(edit.search, self.current_content)
                if actual:
                    self.current_content = self.current_content.replace(actual, edit.content, 1)
                    return EditResult(True, f"Replaced (fuzzy match): {edit.description}")
                    
            return EditResult(False, f"Search text not found: '{edit.search[:50]}...'")
            
        if count > 1:
            # Multiple matches - need more context
            return EditResult(False, f"Multiple matches ({count}) for search text. Provide more context.")
            
        # Exactly one match - safe to replace
        self.current_content = self.current_content.replace(edit.search, edit.content, 1)
        return EditResult(True, f"Replaced: {edit.description}")
        
    def _apply_insert_after(self, edit: CodeEdit) -> EditResult:
        """Insert content after a marker"""
        if not edit.search:
            return EditResult(False, "Insert after requires search text")
        
        # Check if the content to insert already exists in the file
        # This prevents duplicate insertions from multiple steps
        content_stripped = edit.content.strip()
        if content_stripped and content_stripped in self.current_content:
            return EditResult(True, f"Already exists (skipped): {edit.description}")
            
        idx = self.current_content.find(edit.search)
        if idx == -1:
            return EditResult(False, f"Marker not found: '{edit.search[:50]}...'")
            
        insert_pos = idx + len(edit.search)
        
        # Detect indentation of the search line to match it for content
        content = edit.content
        
        # Find the indentation of the line containing the search text
        line_start = self.current_content.rfind('\n', 0, idx) + 1
        line_text = self.current_content[line_start:idx + len(edit.search)]
        search_indent = len(line_text) - len(line_text.lstrip())
        
        # Auto-fix content indentation if it seems wrong
        content_lines = content.split('\n')
        if content_lines and not content_lines[0].strip():
            content_lines = content_lines[1:]  # Remove empty first line
        
        if content_lines:
            first_content_line = content_lines[0] if content_lines else ''
            content_indent = len(first_content_line) - len(first_content_line.lstrip())
            
            # If content is not indented but should be, add indentation
            if content_indent == 0 and search_indent > 0 and first_content_line.strip():
                # Indent all content lines to match search line
                content_lines = [' ' * search_indent + line if line.strip() else line 
                                for line in content_lines]
                content = '\n' + '\n'.join(content_lines)
        
        # Ensure content starts with newline if inserting after a line
        if not content.startswith('\n') and self.current_content[insert_pos:insert_pos+1] not in ('', '\n'):
            content = '\n' + content.lstrip('\n')
        
        # For Python/JS: ensure blank line before new method definitions
        if 'def ' in content or 'function ' in content or 'async def ' in content:
            # Ensure there's a blank line before the new method
            if not content.startswith('\n\n'):
                content = '\n' + content.lstrip('\n')
        
        self.current_content = (
            self.current_content[:insert_pos] + 
            content + 
            self.current_content[insert_pos:]
        )
        return EditResult(True, f"Inserted after: {edit.description}")
        
    def _apply_insert_before(self, edit: CodeEdit) -> EditResult:
        """Insert content before a marker"""
        if not edit.search:
            return EditResult(False, "Insert before requires search text")
        
        # Check if the content to insert already exists in the file
        content_stripped = edit.content.strip()
        if content_stripped and content_stripped in self.current_content:
            return EditResult(True, f"Already exists (skipped): {edit.description}")
            
        idx = self.current_content.find(edit.search)
        if idx == -1:
            return EditResult(False, f"Marker not found: '{edit.search[:50]}...'")
        
        # Ensure content ends with newline when inserting before
        content = edit.content
        if content and not content.endswith('\n'):
            content = content + '\n'
        
        # For Python/JS: ensure blank line between methods/functions
        # Check if SEARCH starts with 'def ' or 'function ' (method boundary)
        if edit.search.strip().startswith(('def ', 'function ', 'async def ', 'async function')):
            if not content.endswith('\n\n') and not content.endswith('\n    \n'):
                # Add extra blank line for PEP8 style
                content = content.rstrip('\n') + '\n\n'
            
        self.current_content = (
            self.current_content[:idx] + 
            content + 
            self.current_content[idx:]
        )
        return EditResult(True, f"Inserted before: {edit.description}")
        
    def _apply_append(self, edit: CodeEdit) -> EditResult:
        """Append to end of file"""
        # Check if content already exists
        content_stripped = edit.content.strip()
        if content_stripped and content_stripped in self.current_content:
            return EditResult(True, f"Already exists (skipped): {edit.description}")
            
        # Ensure newline before append
        if self.current_content and not self.current_content.endswith('\n'):
            self.current_content += '\n'
        self.current_content += edit.content
        return EditResult(True, f"Appended: {edit.description}")
        
    def _apply_prepend(self, edit: CodeEdit) -> EditResult:
        """Prepend to start of file"""
        self.current_content = edit.content + self.current_content
        return EditResult(True, f"Prepended: {edit.description}")
        
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace for fuzzy matching"""
        return re.sub(r'\s+', ' ', text.strip())
        
    def _find_fuzzy_match(self, search: str, content: str) -> Optional[str]:
        """Find text with fuzzy whitespace matching"""
        search_lines = search.strip().split('\n')
        content_lines = content.split('\n')
        
        # Try to find matching sequence of lines
        for i in range(len(content_lines) - len(search_lines) + 1):
            match = True
            for j, search_line in enumerate(search_lines):
                if search_line.strip() != content_lines[i + j].strip():
                    match = False
                    break
            if match:
                # Return the actual text from content
                return '\n'.join(content_lines[i:i + len(search_lines)])
                
        return None
        
    def _generate_diff(self, before: str, after: str) -> str:
        """Generate a unified diff"""
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            before_lines, after_lines,
            fromfile='before', tofile='after',
            lineterm=''
        )
        return ''.join(diff)
        
    def save(self) -> EditResult:
        """Save changes to file"""
        try:
            # Create directory if needed
            dir_path = os.path.dirname(self.file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
                
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.current_content)
                
            return EditResult(
                True, 
                f"Saved {len(self.edits_applied)} edits to {self.file_path}",
                diff=self._generate_diff(self.original_content, self.current_content)
            )
        except Exception as e:
            return EditResult(False, f"Failed to save: {str(e)}")
            
    def rollback(self) -> EditResult:
        """Rollback all changes"""
        self.current_content = self.original_content
        edits_count = len(self.edits_applied)
        self.edits_applied = []
        return EditResult(True, f"Rolled back {edits_count} edits")
        
    def validate_syntax(self) -> EditResult:
        """Validate Python syntax of current content"""
        if not self.file_path.endswith('.py'):
            return EditResult(True, "Not a Python file, skipping syntax check")
            
        try:
            compile(self.current_content, self.file_path, 'exec')
            return EditResult(True, "Syntax valid")
        except SyntaxError as e:
            return EditResult(False, f"Syntax error at line {e.lineno}: {e.msg}")
            
    def get_context_around(self, search: str, lines_before: int = 3, lines_after: int = 3) -> Optional[str]:
        """Get context around a search string for verification"""
        idx = self.current_content.find(search)
        if idx == -1:
            return None
            
        # Find line boundaries
        lines = self.current_content.split('\n')
        current_pos = 0
        target_line = 0
        
        for i, line in enumerate(lines):
            if current_pos + len(line) >= idx:
                target_line = i
                break
            current_pos += len(line) + 1  # +1 for newline
            
        start = max(0, target_line - lines_before)
        end = min(len(lines), target_line + lines_after + 1)
        
        return '\n'.join(lines[start:end])


def parse_llm_edits(llm_response: str) -> List[CodeEdit]:
    """
    Parse LLM response into CodeEdit objects.
    
    Expected format from LLM:
    
    EDIT 1:
    TYPE: replace
    SEARCH:
    ```
    def old_function():
        pass
    ```
    CONTENT:
    ```
    def old_function():
        return "new implementation"
    ```
    DESCRIPTION: Updated function implementation
    
    EDIT 2:
    TYPE: insert_after
    ...
    """
    edits = []
    
    # Split by EDIT markers
    edit_blocks = re.split(r'EDIT\s*\d+\s*:', llm_response, flags=re.IGNORECASE)
    
    for block in edit_blocks[1:]:  # Skip first empty split
        try:
            edit = _parse_single_edit(block)
            if edit:
                edits.append(edit)
        except Exception as e:
            print(f"Warning: Failed to parse edit block: {e}")
            continue
            
    return edits


def _parse_single_edit(block: str) -> Optional[CodeEdit]:
    """Parse a single edit block"""
    # Extract TYPE
    type_match = re.search(r'TYPE:\s*(\w+)', block, re.IGNORECASE)
    if not type_match:
        return None
        
    type_str = type_match.group(1).lower()
    try:
        edit_type = EditType(type_str)
    except ValueError:
        # Try mapping common variations
        type_map = {
            'insert': EditType.INSERT_AFTER,
            'add': EditType.INSERT_AFTER,
            'add_after': EditType.INSERT_AFTER,
            'add_before': EditType.INSERT_BEFORE,
        }
        edit_type = type_map.get(type_str)
        if not edit_type:
            return None
            
    # Extract SEARCH (content between ``` markers)
    search_match = re.search(
        r'SEARCH:\s*```[^\n]*\n(.*?)```',
        block, re.DOTALL | re.IGNORECASE
    )
    search = search_match.group(1).rstrip() if search_match else ""
    
    # Extract CONTENT
    content_match = re.search(
        r'CONTENT:\s*```[^\n]*\n(.*?)```',
        block, re.DOTALL | re.IGNORECASE
    )
    if not content_match:
        return None
    content = content_match.group(1).rstrip()
    
    # Extract DESCRIPTION
    desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else ""
    
    return CodeEdit(
        edit_type=edit_type,
        search=search,
        content=content,
        description=description
    )


# Prompt template for generating precise edits
PRECISE_EDIT_PROMPT = '''You are a surgical code editor. Generate PRECISE edits for the following task.

CURRENT FILE: {file_path}
```
{file_content}
```

TASK: {task}

Generate edits in this EXACT format. Each edit should be minimal and precise.

EDIT 1:
TYPE: [replace|insert_after|insert_before|append]
SEARCH:
```
[exact text to find - include enough context to be unique]
```
CONTENT:
```
[new content to insert or replace with]
```
DESCRIPTION: [what this edit does]

EDIT 2:
...

RULES:
1. SEARCH must match EXACTLY what's in the file (including whitespace and indentation)
2. Include enough context in SEARCH to be unique (usually 3-5 lines)
3. For replace: SEARCH is replaced with CONTENT
4. For insert_after: CONTENT is added after SEARCH (on a new line)
5. For insert_before: CONTENT is added before SEARCH
6. Keep edits minimal - only change what's necessary
7. CRITICAL: Preserve exact indentation levels - count the spaces carefully
8. IMPORTANT: When adding a NEW METHOD after an existing method:
   - Use insert_before with the NEXT method's def line as SEARCH
   - This ensures proper placement between methods
   - Example: To add method B after method A, search for "def next_method" and insert_before
9. Do NOT include the entire file in any edit
10. CONTENT should have a blank line before new method definitions

Generate the minimal set of edits needed. Be precise.'''
