"""
Ryx AI - Context Ranker

Ranks and selects the best context for LLM prompts.
Ensures context fits within token limits while maximizing relevance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

from .semantic_search import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RankedContext:
    """A piece of context with ranking information"""
    content: str
    source: str  # file path or other source
    relevance: float  # 0.0 - 1.0
    tokens: int  # Estimated token count
    priority: int = 5  # 1 = highest, 10 = lowest
    context_type: str = "code"  # code, doc, comment, test
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextRanker:
    """
    Rank and select context for LLM prompts.
    
    Responsibilities:
    1. Estimate token counts
    2. Rank by relevance and priority
    3. Select within budget
    4. Format for LLM
    
    Usage:
    ```python
    ranker = ContextRanker(max_tokens=4000)
    
    # Add context from various sources
    ranker.add_search_results(search_results)
    ranker.add_file("important.py", priority=1)
    
    # Get optimized context
    context = ranker.build_context()
    ```
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        reserve_tokens: int = 500  # For system prompt and response
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self._contexts: List[RankedContext] = []
    
    def add_search_results(
        self,
        results: List[SearchResult],
        priority: int = 5,
        context_type: str = "code"
    ):
        """Add search results as context"""
        for result in results:
            tokens = self._estimate_tokens(result.content)
            self._contexts.append(RankedContext(
                content=result.content,
                source=result.chunk.file_path,
                relevance=result.score,
                tokens=tokens,
                priority=priority,
                context_type=context_type,
                metadata={
                    "start_line": result.chunk.start_line,
                    "end_line": result.chunk.end_line,
                    "language": result.chunk.language
                }
            ))
    
    def add_file(
        self,
        file_path: Path,
        priority: int = 3,
        max_lines: Optional[int] = None,
        relevance: float = 0.8
    ):
        """Add a file as context"""
        path = Path(file_path)
        if not path.exists():
            return
        
        try:
            content = path.read_text(errors='replace')
            
            if max_lines:
                lines = content.split('\n')[:max_lines]
                content = '\n'.join(lines)
            
            tokens = self._estimate_tokens(content)
            
            self._contexts.append(RankedContext(
                content=content,
                source=str(path),
                relevance=relevance,
                tokens=tokens,
                priority=priority,
                context_type="code" if self._is_code_file(path) else "doc",
                metadata={"full_file": max_lines is None}
            ))
        except Exception as e:
            logger.warning(f"Failed to add file {path}: {e}")
    
    def add_text(
        self,
        text: str,
        source: str,
        priority: int = 5,
        relevance: float = 0.5,
        context_type: str = "text"
    ):
        """Add raw text as context"""
        tokens = self._estimate_tokens(text)
        self._contexts.append(RankedContext(
            content=text,
            source=source,
            relevance=relevance,
            tokens=tokens,
            priority=priority,
            context_type=context_type
        ))
    
    def build_context(
        self,
        format: str = "markdown"
    ) -> Tuple[str, List[RankedContext]]:
        """
        Build the final context string.
        
        Returns:
            (formatted_context, selected_contexts)
        """
        available_tokens = self.max_tokens - self.reserve_tokens
        
        # Sort by priority (lower = higher), then by relevance (higher = better)
        sorted_contexts = sorted(
            self._contexts,
            key=lambda c: (c.priority, -c.relevance)
        )
        
        selected = []
        used_tokens = 0
        
        for ctx in sorted_contexts:
            if used_tokens + ctx.tokens <= available_tokens:
                selected.append(ctx)
                used_tokens += ctx.tokens
            elif ctx.priority <= 2:
                # High priority items can be truncated
                remaining = available_tokens - used_tokens
                if remaining > 100:  # Worth including
                    truncated = self._truncate_to_tokens(ctx.content, remaining)
                    ctx.content = truncated
                    ctx.tokens = remaining
                    selected.append(ctx)
                    used_tokens += remaining
                break
        
        # Format output
        if format == "markdown":
            formatted = self._format_markdown(selected)
        elif format == "xml":
            formatted = self._format_xml(selected)
        else:
            formatted = self._format_plain(selected)
        
        return formatted, selected
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Rough estimation: ~4 chars per token for code,
        ~3.5 for prose.
        """
        # More accurate: count words and punctuation
        char_count = len(text)
        word_count = len(text.split())
        
        # Heuristic: mix of char-based and word-based
        return max(
            char_count // 4,
            int(word_count * 1.3)
        )
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token count"""
        # Rough: 4 chars per token
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at a natural break
        truncated = text[:max_chars]
        
        # Find last newline
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars // 2:
            truncated = truncated[:last_newline]
        
        return truncated + "\n... [truncated]"
    
    def _is_code_file(self, path: Path) -> bool:
        """Check if file is code"""
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx',
            '.go', '.rs', '.java', '.cpp', '.c',
            '.rb', '.php', '.sh'
        }
        return path.suffix.lower() in code_extensions
    
    def _format_markdown(self, contexts: List[RankedContext]) -> str:
        """Format contexts as markdown"""
        parts = []
        
        for ctx in contexts:
            language = ctx.metadata.get("language", "")
            source = ctx.source
            
            if ctx.context_type == "code":
                parts.append(f"### {source}")
                if "start_line" in ctx.metadata:
                    parts.append(f"Lines {ctx.metadata['start_line']}-{ctx.metadata['end_line']}")
                parts.append(f"```{language}")
                parts.append(ctx.content)
                parts.append("```")
            else:
                parts.append(f"### {source}")
                parts.append(ctx.content)
            
            parts.append("")
        
        return "\n".join(parts)
    
    def _format_xml(self, contexts: List[RankedContext]) -> str:
        """Format contexts as XML"""
        parts = ["<context>"]
        
        for ctx in contexts:
            parts.append(f'  <file path="{ctx.source}" type="{ctx.context_type}">')
            
            # Escape XML special chars
            content = (ctx.content
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
            
            parts.append(f"    <content>{content}</content>")
            parts.append("  </file>")
        
        parts.append("</context>")
        return "\n".join(parts)
    
    def _format_plain(self, contexts: List[RankedContext]) -> str:
        """Format contexts as plain text"""
        parts = []
        
        for ctx in contexts:
            parts.append(f"=== {ctx.source} ===")
            parts.append(ctx.content)
            parts.append("")
        
        return "\n".join(parts)
    
    def clear(self):
        """Clear all contexts"""
        self._contexts.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ranker statistics"""
        total_tokens = sum(c.tokens for c in self._contexts)
        
        by_type = {}
        for ctx in self._contexts:
            by_type[ctx.context_type] = by_type.get(ctx.context_type, 0) + 1
        
        return {
            "total_contexts": len(self._contexts),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "by_type": by_type,
            "avg_relevance": (
                sum(c.relevance for c in self._contexts) / len(self._contexts)
                if self._contexts else 0
            )
        }
