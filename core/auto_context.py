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
    MAX_CONTEXT_TOKENS = 8000  # Conservative - leave room for system prompt and response
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()
        
    def build_context(self, query: str, max_files: int = 10) -> ContextResult:
        """
        Build context automatically from user query.
        
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
        
        # Find relevant files
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
                
            # Skip if too large
            if len(content) > max_chars * 0.3:  # Single file shouldn't be >30% of context
                content = self._truncate_smart(content, int(max_chars * 0.3))
            
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
        skip_terms = {'does', 'what', 'how', 'why', 'the', 'this', 'that', 'have', 'has'}
        meaningful_terms = [t for t in terms if t not in skip_terms and len(t) >= 3]
        
        for term in meaningful_terms[:5]:  # Use top 5 meaningful terms
            # Search file names with find
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
            
            # Also search by PATH containing the term (finds files in directories like ryxsurf/)
            try:
                result = subprocess.run(
                    ['find', str(self.repo_root), '-type', 'f', '-path', f'*{term}*'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        found_files.add(Path(line))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Search file contents with ripgrep (only for specific terms, not common words)
            if len(term) >= 4:  # Only search content for longer terms
                try:
                    result = subprocess.run(
                        ['rg', '-l', '-i', '--max-count=1', '--max-depth=5', term, str(self.repo_root)],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            found_files.add(Path(line))
                except (subprocess.TimeoutExpired, FileNotFoundError):
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
    
    def _read_file(self, path: Path) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(path, 'r', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.debug(f"Failed to read {path}: {e}")
            return None
    
    def _truncate_smart(self, content: str, max_chars: int) -> str:
        """Truncate content intelligently (at line boundaries)"""
        if len(content) <= max_chars:
            return content
        
        # Find a good breaking point
        lines = content[:max_chars].split('\n')
        
        # Keep complete lines
        result = '\n'.join(lines[:-1])
        result += f"\n\n... (truncated {len(content) - len(result)} chars)"
        
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
