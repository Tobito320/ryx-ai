"""
Ryx Editing Module

Provides diff-based file editing for safe code modifications.
Inspired by Aider's search/replace approach.

Key Components:
- DiffEditor: Apply unified diffs to files
- SearchReplace: Search/replace block editing
- EditValidator: Validate edits before applying

Usage:
    from ryx_pkg.editing import DiffEditor, apply_edit
    
    editor = DiffEditor()
    result = editor.apply_diff(file_path, diff_text)
"""

from .diff_editor import DiffEditor, DiffResult
from .search_replace import SearchReplace, find_and_replace
from .validator import EditValidator, ValidationResult

__all__ = [
    'DiffEditor',
    'DiffResult',
    'SearchReplace',
    'find_and_replace',
    'EditValidator',
    'ValidationResult',
]
