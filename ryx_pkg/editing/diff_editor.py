"""
Ryx Diff Editor

Apply unified diffs and patches to files.
Provides safe file editing with backup and validation.

Inspired by Aider's diff handling.
"""

import os
import re
import shutil
import difflib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    """A single hunk from a unified diff"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str] = field(default_factory=list)


@dataclass
class DiffResult:
    """Result of applying a diff"""
    success: bool
    file_path: str
    message: str
    backup_path: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0
    hunks_applied: int = 0
    hunks_failed: int = 0


class DiffEditor:
    """
    Unified diff editor for Ryx.
    
    Applies unified diffs to files with:
    - Automatic backup creation
    - Fuzzy matching for context lines
    - Detailed error reporting
    - Dry-run mode
    """
    
    BACKUP_DIR = ".ryx.backups"
    
    def __init__(
        self,
        root: str = None,
        create_backups: bool = True,
        fuzzy_threshold: float = 0.8
    ):
        """
        Initialize DiffEditor.
        
        Args:
            root: Root directory for relative paths
            create_backups: Create backup files before editing
            fuzzy_threshold: Threshold for fuzzy line matching (0-1)
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.create_backups = create_backups
        self.fuzzy_threshold = fuzzy_threshold
    
    def apply_diff(
        self,
        file_path: str,
        diff_text: str,
        dry_run: bool = False
    ) -> DiffResult:
        """
        Apply a unified diff to a file.
        
        Args:
            file_path: Path to the file (absolute or relative to root)
            diff_text: Unified diff text
            dry_run: If True, don't actually modify the file
            
        Returns:
            DiffResult with status and details
        """
        # Resolve file path
        if not os.path.isabs(file_path):
            full_path = self.root / file_path
        else:
            full_path = Path(file_path)
        
        # Check if file exists
        if not full_path.exists():
            return DiffResult(
                success=False,
                file_path=str(file_path),
                message=f"File not found: {file_path}"
            )
        
        # Parse the diff
        hunks = self._parse_diff(diff_text)
        
        if not hunks:
            return DiffResult(
                success=False,
                file_path=str(file_path),
                message="No valid hunks found in diff"
            )
        
        # Read original file
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
        except Exception as e:
            return DiffResult(
                success=False,
                file_path=str(file_path),
                message=f"Error reading file: {e}"
            )
        
        # Apply hunks
        new_lines, applied, failed = self._apply_hunks(original_lines, hunks)
        
        if failed > 0 and applied == 0:
            return DiffResult(
                success=False,
                file_path=str(file_path),
                message=f"Failed to apply any hunks ({failed} failed)",
                hunks_failed=failed
            )
        
        if dry_run:
            # Calculate stats without writing
            lines_added = sum(1 for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++'))
            lines_removed = sum(1 for l in diff_text.split('\n') if l.startswith('-') and not l.startswith('---'))
            
            return DiffResult(
                success=True,
                file_path=str(file_path),
                message=f"Dry run: {applied} hunks would be applied",
                lines_added=lines_added,
                lines_removed=lines_removed,
                hunks_applied=applied,
                hunks_failed=failed
            )
        
        # Create backup
        backup_path = None
        if self.create_backups:
            backup_path = self._create_backup(full_path)
        
        # Write new content
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            # Restore from backup if write failed
            if backup_path:
                shutil.copy2(backup_path, full_path)
            
            return DiffResult(
                success=False,
                file_path=str(file_path),
                message=f"Error writing file: {e}"
            )
        
        lines_added = sum(1 for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++'))
        lines_removed = sum(1 for l in diff_text.split('\n') if l.startswith('-') and not l.startswith('---'))
        
        return DiffResult(
            success=True,
            file_path=str(file_path),
            message=f"Applied {applied} hunk(s)" + (f", {failed} failed" if failed else ""),
            backup_path=backup_path,
            lines_added=lines_added,
            lines_removed=lines_removed,
            hunks_applied=applied,
            hunks_failed=failed
        )
    
    def _parse_diff(self, diff_text: str) -> List[DiffHunk]:
        """Parse unified diff into hunks"""
        hunks = []
        current_hunk = None
        
        for line in diff_text.split('\n'):
            # Match hunk header: @@ -old_start,old_count +new_start,new_count @@
            hunk_match = re.match(r'^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@', line)
            
            if hunk_match:
                if current_hunk:
                    hunks.append(current_hunk)
                
                current_hunk = DiffHunk(
                    old_start=int(hunk_match.group(1)),
                    old_count=int(hunk_match.group(2) or 1),
                    new_start=int(hunk_match.group(3)),
                    new_count=int(hunk_match.group(4) or 1),
                    lines=[]
                )
            elif current_hunk is not None:
                if line.startswith('+') or line.startswith('-') or line.startswith(' '):
                    current_hunk.lines.append(line)
                elif line.startswith('\\'):
                    # "\ No newline at end of file" - skip
                    pass
        
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def _apply_hunks(
        self,
        lines: List[str],
        hunks: List[DiffHunk]
    ) -> Tuple[List[str], int, int]:
        """Apply hunks to lines, return new lines and counts"""
        result = list(lines)
        offset = 0
        applied = 0
        failed = 0
        
        for hunk in hunks:
            success, result, delta = self._apply_hunk(result, hunk, offset)
            
            if success:
                applied += 1
                offset += delta
            else:
                failed += 1
        
        return result, applied, failed
    
    def _apply_hunk(
        self,
        lines: List[str],
        hunk: DiffHunk,
        offset: int
    ) -> Tuple[bool, List[str], int]:
        """
        Apply a single hunk.
        
        Returns (success, new_lines, offset_delta)
        """
        # Calculate actual position with offset
        pos = hunk.old_start - 1 + offset
        
        # Extract context and changes from hunk
        old_lines = []
        new_lines = []
        
        for line in hunk.lines:
            if line.startswith('-'):
                old_lines.append(line[1:] + '\n' if not line[1:].endswith('\n') else line[1:])
            elif line.startswith('+'):
                new_lines.append(line[1:] + '\n' if not line[1:].endswith('\n') else line[1:])
            elif line.startswith(' '):
                content = line[1:] + '\n' if not line[1:].endswith('\n') else line[1:]
                old_lines.append(content)
                new_lines.append(content)
        
        # Try exact match first
        if pos >= 0 and pos + len(old_lines) <= len(lines):
            if self._lines_match(lines[pos:pos + len(old_lines)], old_lines):
                # Apply the change
                result = lines[:pos] + new_lines + lines[pos + len(old_lines):]
                delta = len(new_lines) - len(old_lines)
                return True, result, delta
        
        # Try fuzzy matching
        match_pos = self._find_fuzzy_match(lines, old_lines, pos)
        
        if match_pos is not None:
            result = lines[:match_pos] + new_lines + lines[match_pos + len(old_lines):]
            delta = len(new_lines) - len(old_lines)
            logger.debug(f"Fuzzy match at line {match_pos + 1} (expected {pos + 1})")
            return True, result, delta
        
        return False, lines, 0
    
    def _lines_match(self, actual: List[str], expected: List[str]) -> bool:
        """Check if lines match (ignoring trailing whitespace)"""
        if len(actual) != len(expected):
            return False
        
        for a, e in zip(actual, expected):
            if a.rstrip() != e.rstrip():
                return False
        
        return True
    
    def _find_fuzzy_match(
        self,
        lines: List[str],
        target: List[str],
        hint_pos: int
    ) -> Optional[int]:
        """Find the best fuzzy match position for target lines"""
        if not target:
            return None
        
        best_pos = None
        best_ratio = 0
        
        # Search around the hint position first
        search_range = min(50, len(lines))
        
        for offset in range(search_range):
            for pos in [hint_pos + offset, hint_pos - offset]:
                if pos < 0 or pos + len(target) > len(lines):
                    continue
                
                # Calculate similarity
                actual = lines[pos:pos + len(target)]
                ratio = self._calculate_similarity(actual, target)
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_pos = pos
                
                if ratio >= 0.99:  # Good enough
                    return pos
        
        if best_ratio >= self.fuzzy_threshold:
            return best_pos
        
        return None
    
    def _calculate_similarity(self, lines1: List[str], lines2: List[str]) -> float:
        """Calculate similarity between two line lists"""
        text1 = ''.join(lines1)
        text2 = ''.join(lines2)
        
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _create_backup(self, file_path: Path) -> str:
        """Create a backup of the file"""
        backup_dir = self.root / self.BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        
        return str(backup_path)
    
    def generate_diff(
        self,
        original: str,
        modified: str,
        file_path: str = "file",
        context_lines: int = 3
    ) -> str:
        """
        Generate a unified diff between two strings.
        
        Args:
            original: Original content
            modified: Modified content
            file_path: File name for diff header
            context_lines: Number of context lines
            
        Returns:
            Unified diff string
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=context_lines
        )
        
        return ''.join(diff)
    
    def restore_backup(self, backup_path: str, original_path: str = None) -> bool:
        """
        Restore a file from backup.
        
        Args:
            backup_path: Path to backup file
            original_path: Original file path (extracted from backup name if None)
            
        Returns:
            True if restored successfully
        """
        backup = Path(backup_path)
        
        if not backup.exists():
            logger.warning(f"Backup not found: {backup_path}")
            return False
        
        if original_path is None:
            # Try to extract from backup name (name.timestamp.bak)
            parts = backup.name.rsplit('.', 2)
            if len(parts) >= 3:
                original_path = parts[0]
        
        if original_path is None:
            logger.warning("Could not determine original file path")
            return False
        
        try:
            shutil.copy2(backup, original_path)
            logger.info(f"Restored {original_path} from backup")
            return True
        except Exception as e:
            logger.error(f"Failed to restore: {e}")
            return False
