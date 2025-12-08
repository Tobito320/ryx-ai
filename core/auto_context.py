"""
Ryx AI - Automatic Context Builder

THE KEY DIFFERENTIATOR from Aider/Claude Code:
- User NEVER needs to add files manually
- Ryx automatically discovers and loads relevant files
- Smarter than all other tools

Flow:
1. User asks: "fix the vLLM client timeout issue"
2. Ryx automatically:
   - Finds files matching "vllm", "client", "timeout"
   - Reads the most relevant ones
   - Builds context for the LLM
   - LLM can now edit files directly

Uses:
- ripgrep (rg) for content search
- fd for file discovery  
- RepoExplorer for caching
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    """A file with its content for LLM context"""
    path: str
    content: str
    relevance: float  # 0.0 to 1.0
    reason: str  # Why this file was included
    lines: int
    
    def to_prompt(self) -> str:
        """Format for LLM prompt"""
        return f"""<file path="{self.path}" lines="{self.lines}" relevance="{self.relevance:.2f}">
{self.content}
</file>"""


@dataclass  
class ContextResult:
    """Result of automatic context building"""
    files: List[FileContext] = field(default_factory=list)
    total_tokens_estimate: int = 0
    search_terms: List[str] = field(default_factory=list)
    
    def to_prompt(self) -> str:
        """Generate full context prompt"""
        if not self.files:
            return ""
        
        header = f"I have automatically loaded {len(self.files)} relevant files for you:\n\n"
        files_content = "\n\n".join(f.to_prompt() for f in self.files)
        footer = "\n\nYou can read and edit these files. Use precise edits."
        
        return header + files_content + footer


class AutoContextBuilder:
    """
    Automatically builds context for LLM based on user query.
    
    This is what makes Ryx better than Aider - no manual file adding!
    """
    
    # Keywords that indicate file-related queries
    FILE_INDICATORS = [
        'file', 'code', 'function', 'class', 'method', 'module',
        'fix', 'edit', 'change', 'update', 'modify', 'refactor',
        'add', 'create', 'implement', 'bug', 'error', 'issue',
        'read', 'show', 'view', 'open', 'find', 'search', 'look'
    ]
    
    # Max context size (tokens estimate: ~4 chars per token)
    MAX_CONTEXT_TOKENS = 12000  # Increased for better coverage of large files
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()
        # Initialize RepoMap for smarter file discovery
        try:
            from core.repo_map import get_repo_map
            self.repo_map = get_repo_map(str(self.repo_root))
        except ImportError:
            self.repo_map = None
        
    def build_context(self, query: str, max_files: int = 10) -> ContextResult:
        """
        Build context automatically from user query.
        
        Uses RepoMap for semantic code understanding when available,
        falls back to simple file search otherwise.
        
        Args:
            query: User's natural language query
            max_files: Maximum files to include
            
        Returns:
            ContextResult with relevant files
        """
        result = ContextResult()
        
        # Extract search terms from query
        search_terms = self._extract_search_terms(query)
        result.search_terms = search_terms
        
        if not search_terms:
            return result
        
        # Try RepoMap first (smarter, uses code structure)
        if self.repo_map:
            try:
                relevant = self.repo_map.get_relevant_files(query, max_files * 2)
                if relevant:
                    logger.debug(f"RepoMap found {len(relevant)} relevant files")
                    return self._build_from_repo_map(relevant, result, query, max_files)
            except Exception as e:
                logger.debug(f"RepoMap failed, falling back: {e}")
        
        # Fallback to basic file search
        relevant_files = self._find_relevant_files(search_terms, max_files * 2)
        
        # Score and sort by relevance
        scored_files = self._score_files(relevant_files, search_terms, query)
        
        # Load file contents (respecting token limit)
        total_chars = 0
        max_chars = self.MAX_CONTEXT_TOKENS * 4  # Rough estimate
        
        for path, score, reason in scored_files[:max_files]:
            if total_chars >= max_chars:
                break
                
            content = self._read_file(path)
            if content is None:
                continue
                
            # Skip if too large - use smart truncation with search terms
            if len(content) > max_chars * 0.3:  # Single file shouldn't be >30% of context
                content = self._truncate_smart(content, int(max_chars * 0.3), search_terms)
            
            file_ctx = FileContext(
                path=str(path.relative_to(self.repo_root)),
                content=content,
                relevance=score,
                reason=reason,
                lines=content.count('\n') + 1
            )
            
            result.files.append(file_ctx)
            total_chars += len(content)
        
        result.total_tokens_estimate = total_chars // 4
        return result
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from natural language query"""
        terms = []
        
        # Lowercase and clean
        query_lower = query.lower()
        
        # Extract quoted strings first (exact matches)
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        terms.extend(quoted)
        
        # Extract file paths/names mentioned
        # Patterns like: file.py, path/to/file, @file.py
        file_patterns = re.findall(r'@?([\w/.-]+\.\w+)', query)
        terms.extend(file_patterns)
        
        # Extract directory mentions
        dir_patterns = re.findall(r'(?:in|from|at)\s+(\w+(?:/\w+)*)', query_lower)
        terms.extend(dir_patterns)
        
        # Extract technical terms (camelCase, snake_case, PascalCase)
        tech_terms = re.findall(r'\b([A-Z][a-z]+[A-Z]\w*|\w+_\w+|[A-Z]{2,}[a-z]+\w*)\b', query)
        terms.extend(t.lower() for t in tech_terms)
        
        # Extract significant nouns/verbs (skip common words)
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my',
            'you', 'your', 'we', 'our', 'they', 'their', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'all', 'any', 'both',
            'each', 'few', 'more', 'most', 'some', 'such', 'no', 'not',
            'only', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
            'now', 'here', 'there', 'then', 'if', 'or', 'and', 'but',
            'about', 'after', 'before', 'between', 'into', 'through',
            'during', 'above', 'below', 'to', 'from', 'up', 'down',
            'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further',
            'tell', 'show', 'explain', 'make', 'get', 'want', 'need',
            'please', 'help', 'like', 'know', 'think', 'see', 'look',
            'file', 'files', 'code', 'read', 'write', 'edit', 'change'
        }
        
        words = re.findall(r'\b(\w{3,})\b', query_lower)
        for word in words:
            if word not in stop_words and word not in terms:
                terms.append(word)
        
        # Deduplicate while preserving order
        seen = set()
        unique_terms = []
        for t in terms:
            t_lower = t.lower()
            if t_lower not in seen and len(t_lower) >= 2:
                seen.add(t_lower)
                unique_terms.append(t_lower)
        
        return unique_terms[:15]  # Limit search terms
    
    def _find_relevant_files(self, terms: List[str], max_results: int) -> List[Path]:
        """Find files matching search terms using ripgrep and find"""
        found_files: Set[Path] = set()
        
        # Filter out very common words that would match too many files
        skip_terms = {'does', 'what', 'how', 'why', 'the', 'this', 'that', 'have', 'has', 'add'}
        
        # Prioritize filename patterns (like browser.py) over directory names
        filename_terms = [t for t in terms if '.' in t]
        other_terms = [t for t in terms if '.' not in t and t not in skip_terms and len(t) >= 3]
        meaningful_terms = filename_terms + other_terms
        
        for term in meaningful_terms[:5]:  # Use top 5 meaningful terms
            # Search file names with find (most specific)
            try:
                result = subprocess.run(
                    ['find', str(self.repo_root), '-type', 'f', '-iname', f'*{term}*'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        found_files.add(Path(line))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Limit path searches to avoid grabbing entire directories
            if len(found_files) < max_results:
                try:
                    result = subprocess.run(
                        ['find', str(self.repo_root), '-type', 'f', '-path', f'*{term}*'],
                        capture_output=True, text=True, timeout=5
                    )
                    count = 0
                    for line in result.stdout.strip().split('\n'):
                        if line and count < max_results:
                            found_files.add(Path(line))
                            count += 1
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
            
            # Search file contents (only for specific terms)
            if len(term) >= 4 and len(found_files) < max_results:
                try:
                    result = subprocess.run(
                        ['rg', '-l', '-i', '--max-count=1', '--max-depth=5', term, str(self.repo_root)],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            found_files.add(Path(line))
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # Fallback to grep
                    try:
                        result = subprocess.run(
                            ['grep', '-rl', term, str(self.repo_root)],
                            capture_output=True, text=True, timeout=10
                        )
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                found_files.add(Path(line))
                    except:
                        pass
        
        # Filter out non-code files and binaries
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.rb',
            '.java', '.kt', '.c', '.cpp', '.h', '.hpp', '.cs', '.sh',
            '.yaml', '.yml', '.json', '.toml', '.md', '.txt', '.html',
            '.css', '.scss', '.lua', '.vim', '.el'
        }
        
        filtered = [
            f for f in found_files 
            if f.suffix.lower() in code_extensions
            and not any(skip in str(f) for skip in [
                'node_modules', '__pycache__', '.git', 'venv', '.venv',
                'dist', 'build', '.egg-info'
            ])
        ]
        
        return list(filtered)[:max_results]
    
    def _score_files(
        self, 
        files: List[Path], 
        terms: List[str],
        query: str
    ) -> List[Tuple[Path, float, str]]:
        """Score files by relevance to query"""
        scored = []
        
        for file_path in files:
            score = 0.0
            reasons = []
            
            file_name = file_path.name.lower()
            file_str = str(file_path).lower()
            
            # Count how many terms match in path (most important!)
            path_term_matches = sum(1 for t in terms if t in file_str)
            if path_term_matches > 1:
                # Multiple terms = very relevant
                score += 0.5 * path_term_matches
                reasons.append(f"{path_term_matches} terms in path")
            elif path_term_matches == 1:
                score += 0.3
                for t in terms:
                    if t in file_str:
                        reasons.append(f"path contains '{t}'")
                        break
            
            # Filename match bonus
            for term in terms:
                if term in file_name:
                    score += 0.3
                    if f"filename contains '{term}'" not in reasons:
                        reasons.append(f"filename contains '{term}'")
            
            # Content match (check first few KB)
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    content_preview = f.read(4000).lower()
                    
                term_matches = sum(1 for t in terms if t in content_preview)
                if term_matches > 0:
                    score += min(0.3, term_matches * 0.1)
                    reasons.append(f"{term_matches} terms in content")
            except:
                pass
            
            # Boost for likely important files
            important_patterns = ['main', 'core', 'brain', 'agent', 'config', 'api']
            if any(p in file_name for p in important_patterns):
                score += 0.1
            
            if score > 0:
                reason = "; ".join(reasons) if reasons else "related"
                scored.append((file_path, min(1.0, score), reason))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _build_from_repo_map(self, repo_map_results, result: ContextResult, query: str, max_files: int) -> ContextResult:
        """Build context from RepoMap results (smarter, uses code structure)"""
        total_chars = 0
        max_chars = self.MAX_CONTEXT_TOKENS * 4
        search_terms = result.search_terms
        
        for file_info in repo_map_results[:max_files]:
            if total_chars >= max_chars:
                break
            
            path = self.repo_root / file_info.path
            content = self._read_file(path)
            if content is None:
                continue
            
            # Smart truncation for large files
            if len(content) > max_chars * 0.3:
                content = self._truncate_smart(content, int(max_chars * 0.3), search_terms)
            
            # Build reason from symbols
            symbol_names = [s.name for s in file_info.symbols[:5]]
            reason = f"symbols: {', '.join(symbol_names)}" if symbol_names else "relevant"
            
            file_ctx = FileContext(
                path=file_info.path,
                content=content,
                relevance=0.8,  # RepoMap results are pre-scored
                reason=reason,
                lines=content.count('\n') + 1
            )
            
            result.files.append(file_ctx)
            total_chars += len(content)
        
        result.total_tokens_estimate = total_chars // 4
        return result
    
    def _read_file(self, path: Path) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(path, 'r', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.debug(f"Failed to read {path}: {e}")
            return None
    
    def _truncate_smart(self, content: str, max_chars: int, search_terms: List[str] = None) -> str:
        """
        Truncate content intelligently - keep relevant sections.
        
        Prioritizes sections with specific search terms over generic matches.
        """
        if len(content) <= max_chars:
            return content
        
        lines = content.split('\n')
        
        if search_terms:
            # Separate specific terms (with underscore, dots) from generic ones
            specific_terms = [t for t in search_terms if '_' in t or '.' in t]
            generic_terms = [t for t in search_terms if '_' not in t and '.' not in t]
            
            # Also look for def/class definitions that might be relevant
            # This helps when user says "add method after X" - we find X
            def_lines = []
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') or line.strip().startswith('class '):
                    def_lines.append(i)
            
            # Find ranges for specific terms first (higher priority)
            priority_ranges = []
            other_ranges = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # Check specific terms
                if any(term in line_lower for term in specific_terms):
                    start = max(0, i - 20)
                    end = min(len(lines), i + 50)  # More context for important matches
                    priority_ranges.append((start, end, True))  # True = priority
                # Check generic terms
                elif any(term in line_lower for term in generic_terms):
                    start = max(0, i - 10)
                    end = min(len(lines), i + 20)  # Less context for generic matches
                    other_ranges.append((start, end, False))
            
            # Combine with priority first
            all_ranges = priority_ranges + other_ranges
            
            if all_ranges:
                # Sort priority first, then by line number
                all_ranges.sort(key=lambda x: (not x[2], x[0]))
                
                # Build sections
                sections = []
                total_len = 0
                included_lines = set()
                
                # Always include file header
                header = '\n'.join(lines[:25])
                sections.append(header)
                total_len += len(header)
                for i in range(25):
                    included_lines.add(i)
                
                for start, end, is_priority in all_ranges:
                    if total_len >= max_chars:
                        break
                    
                    # Skip if already included
                    if all(i in included_lines for i in range(start, end)):
                        continue
                    
                    section_lines = []
                    for i in range(start, end):
                        if i not in included_lines:
                            section_lines.append(lines[i])
                            included_lines.add(i)
                    
                    if section_lines:
                        section = '\n'.join(section_lines)
                        if total_len + len(section) <= max_chars or is_priority:
                            # Always include priority sections even if over limit
                            sections.append(f"\n... (lines {start+1}-{end}) ...\n")
                            sections.append(section)
                            total_len += len(section)
                
                result = '\n'.join(sections)
                if len(content) > len(result):
                    result += f"\n\n... ({len(content) - len(result)} chars omitted)"
                return result
        
        # Fallback
        result = '\n'.join(lines[:max_chars // 50])
        result += f"\n\n... (truncated)"
        return result


def build_context_for_query(query: str, repo_root: str = ".") -> ContextResult:
    """Convenience function to build context"""
    builder = AutoContextBuilder(repo_root)
    return builder.build_context(query)


# Test
if __name__ == "__main__":
    import sys
    
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "vllm client"
    
    builder = AutoContextBuilder("/home/tobi/ryx-ai")
    result = builder.build_context(query)
    
    print(f"Search terms: {result.search_terms}")
    print(f"Found {len(result.files)} files ({result.total_tokens_estimate} tokens est.)")
    print()
    
    for f in result.files:
        print(f"  {f.path} (relevance: {f.relevance:.2f}) - {f.reason}")
