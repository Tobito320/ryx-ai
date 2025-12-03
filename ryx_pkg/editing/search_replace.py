"""
Ryx Search/Replace Editor

Search and replace block-based editing for Ryx.
Similar to Aider's SEARCH/REPLACE blocks.

Provides:
- Fuzzy text matching
- Multi-block replacements
- Whitespace-tolerant matching
"""

import os
import re
import difflib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReplaceBlock:
    """A search/replace block"""
    search: str
    replace: str
    file_path: Optional[str] = None


@dataclass
class ReplaceResult:
    """Result of a search/replace operation"""
    success: bool
    file_path: str
    message: str
    matches_found: int = 0
    replacements_made: int = 0


class SearchReplace:
    """
    Search and replace editor.
    
    Supports:
    - Exact matching
    - Fuzzy matching with configurable threshold
    - Whitespace normalization
    - Multi-block operations
    """
    
    def __init__(
        self,
        root: str = None,
        fuzzy_threshold: float = 0.8,
        ignore_whitespace: bool = True
    ):
        """
        Initialize SearchReplace.
        
        Args:
            root: Root directory for relative paths
            fuzzy_threshold: Threshold for fuzzy matching (0-1)
            ignore_whitespace: Ignore leading/trailing whitespace
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.fuzzy_threshold = fuzzy_threshold
        self.ignore_whitespace = ignore_whitespace
    
    def replace_in_file(
        self,
        file_path: str,
        search: str,
        replace: str,
        all_occurrences: bool = False
    ) -> ReplaceResult:
        """
        Replace text in a file.
        
        Args:
            file_path: Path to the file
            search: Text to search for
            replace: Replacement text
            all_occurrences: Replace all matches (default: first only)
            
        Returns:
            ReplaceResult with status and details
        """
        # Resolve path
        if not os.path.isabs(file_path):
            full_path = self.root / file_path
        else:
            full_path = Path(file_path)
        
        if not full_path.exists():
            return ReplaceResult(
                success=False,
                file_path=str(file_path),
                message=f"File not found: {file_path}"
            )
        
        # Read file
        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception as e:
            return ReplaceResult(
                success=False,
                file_path=str(file_path),
                message=f"Error reading file: {e}"
            )
        
        # Try exact match first
        if search in content:
            if all_occurrences:
                count = content.count(search)
                new_content = content.replace(search, replace)
            else:
                count = 1
                new_content = content.replace(search, replace, 1)
            
            try:
                full_path.write_text(new_content, encoding='utf-8')
                return ReplaceResult(
                    success=True,
                    file_path=str(file_path),
                    message=f"Replaced {count} occurrence(s)",
                    matches_found=content.count(search) if all_occurrences else 1,
                    replacements_made=count
                )
            except Exception as e:
                return ReplaceResult(
                    success=False,
                    file_path=str(file_path),
                    message=f"Error writing file: {e}"
                )
        
        # Try fuzzy match
        match_result = self._fuzzy_find(content, search)
        
        if match_result:
            start, end = match_result
            new_content = content[:start] + replace + content[end:]
            
            try:
                full_path.write_text(new_content, encoding='utf-8')
                return ReplaceResult(
                    success=True,
                    file_path=str(file_path),
                    message="Replaced with fuzzy match",
                    matches_found=1,
                    replacements_made=1
                )
            except Exception as e:
                return ReplaceResult(
                    success=False,
                    file_path=str(file_path),
                    message=f"Error writing file: {e}"
                )
        
        return ReplaceResult(
            success=False,
            file_path=str(file_path),
            message="Search text not found"
        )
    
    def replace_blocks(
        self,
        blocks: List[ReplaceBlock],
        default_file: str = None
    ) -> List[ReplaceResult]:
        """
        Apply multiple replace blocks.
        
        Args:
            blocks: List of ReplaceBlock to apply
            default_file: Default file if block doesn't specify one
            
        Returns:
            List of ReplaceResult for each block
        """
        results = []
        
        for block in blocks:
            file_path = block.file_path or default_file
            
            if not file_path:
                results.append(ReplaceResult(
                    success=False,
                    file_path="",
                    message="No file path specified"
                ))
                continue
            
            result = self.replace_in_file(
                file_path,
                block.search,
                block.replace
            )
            results.append(result)
        
        return results
    
    def _fuzzy_find(self, content: str, search: str) -> Optional[Tuple[int, int]]:
        """
        Find the best fuzzy match for search in content.
        
        Returns (start, end) tuple if found, None otherwise.
        """
        if self.ignore_whitespace:
            search = self._normalize_whitespace(search)
        
        search_lines = search.split('\n')
        content_lines = content.split('\n')
        
        best_match = None
        best_ratio = 0
        
        # Sliding window search
        window_size = len(search_lines)
        
        for i in range(len(content_lines) - window_size + 1):
            window = content_lines[i:i + window_size]
            window_text = '\n'.join(window)
            
            if self.ignore_whitespace:
                window_text = self._normalize_whitespace(window_text)
            
            ratio = difflib.SequenceMatcher(None, search, window_text).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (i, i + window_size)
        
        if best_ratio >= self.fuzzy_threshold and best_match:
            # Calculate character positions
            start_pos = sum(len(line) + 1 for line in content_lines[:best_match[0]])
            end_pos = sum(len(line) + 1 for line in content_lines[:best_match[1]])
            
            # Adjust for final newline
            if end_pos > len(content):
                end_pos = len(content)
            
            return (start_pos, end_pos)
        
        return None
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        lines = text.split('\n')
        normalized = [line.strip() for line in lines]
        return '\n'.join(normalized)
    
    def parse_blocks(self, text: str) -> List[ReplaceBlock]:
        """
        Parse SEARCH/REPLACE blocks from text.
        
        Format:
        <<<<<<< SEARCH
        text to find
        =======
        replacement text
        >>>>>>> REPLACE
        
        Args:
            text: Text containing blocks
            
        Returns:
            List of ReplaceBlock
        """
        blocks = []
        
        # Pattern for search/replace blocks
        pattern = r'<<<<<<+\s*SEARCH\s*\n(.*?)\n=======+\s*\n(.*?)\n>>>>>>>+\s*REPLACE'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            search_text = match.group(1)
            replace_text = match.group(2)
            
            blocks.append(ReplaceBlock(
                search=search_text,
                replace=replace_text
            ))
        
        # Also try simplified format
        simple_pattern = r'```search\n(.*?)\n```\s*```replace\n(.*?)\n```'
        
        for match in re.finditer(simple_pattern, text, re.DOTALL):
            blocks.append(ReplaceBlock(
                search=match.group(1),
                replace=match.group(2)
            ))
        
        return blocks


def find_and_replace(
    file_path: str,
    search: str,
    replace: str,
    root: str = None
) -> ReplaceResult:
    """
    Convenience function for simple search/replace.
    
    Args:
        file_path: Path to the file
        search: Text to search for
        replace: Replacement text
        root: Root directory
        
    Returns:
        ReplaceResult
    """
    editor = SearchReplace(root=root)
    return editor.replace_in_file(file_path, search, replace)
