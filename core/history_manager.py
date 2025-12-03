"""
History and Context Management for Ryx.

Inspired by Claude Code's history control patterns.
Manages conversation history, context window, and message compression.
"""

import copy
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path
import os


class Role(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class CropDirection(str, Enum):
    """Direction for cropping history."""
    TOP = "top"      # Remove oldest messages (after system)
    BOTTOM = "bottom"  # Remove newest messages (before current)


@dataclass
class TokenUsage:
    """Token usage tracking."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, other: 'TokenUsage'):
        """Add another usage to this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens


@dataclass
class Message:
    """A conversation message."""
    role: Role
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For tool messages
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-compatible dict."""
        d = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dict."""
        return cls(
            role=Role(data.get("role", "user")),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )


class HistoryManager:
    """
    Manages conversation history with compression and context control.
    
    Features:
    - Token tracking
    - Auto-compression when context window fills
    - Smart cropping (preserve system + recent messages)
    - Session persistence
    
    Usage:
        history = HistoryManager(max_tokens=128000)
        history.add_message(Message(Role.USER, "Hello"))
        history.add_message(Message(Role.ASSISTANT, "Hi there!"))
        
        # Auto-compress if needed
        history.auto_compress()
        
        # Get messages for API
        messages = history.get_messages()
    """
    
    def __init__(
        self, 
        max_tokens: int = 128000,
        compress_threshold: float = 0.8,
        preserve_recent: int = 5
    ):
        """
        Initialize history manager.
        
        Args:
            max_tokens: Maximum context window size
            compress_threshold: Compress when usage exceeds this ratio
            preserve_recent: Always preserve this many recent message pairs
        """
        self.max_tokens = max_tokens
        self.compress_threshold = compress_threshold
        self.preserve_recent = preserve_recent
        
        self._messages: List[Message] = []
        self._token_usage = TokenUsage()
        self._compression_count = 0
    
    @property
    def messages(self) -> List[Message]:
        """Get current messages."""
        return self._messages
    
    @property
    def context_usage(self) -> float:
        """Get context window usage as percentage."""
        if self.max_tokens == 0:
            return 0.0
        return (self._token_usage.total_tokens / self.max_tokens) * 100
    
    @property
    def context_usage_str(self) -> str:
        """Get context usage as formatted string."""
        return f"{self.context_usage:.1f}%"
    
    def add_message(self, message: Message):
        """Add a message to history."""
        self._messages.append(message)
        # Rough token estimate (will be updated by actual usage)
        estimated_tokens = len(message.content) // 4
        self._token_usage.input_tokens += estimated_tokens
        self._token_usage.total_tokens += estimated_tokens
    
    def add_user_message(self, content: str):
        """Add a user message."""
        self.add_message(Message(Role.USER, content))
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add an assistant message."""
        self.add_message(Message(Role.ASSISTANT, content, tool_calls=tool_calls))
    
    def add_tool_message(self, tool_call_id: str, name: str, content: str):
        """Add a tool response message."""
        self.add_message(Message(
            Role.TOOL, content, 
            tool_call_id=tool_call_id, 
            name=name
        ))
    
    def add_system_message(self, content: str):
        """Add or update system message."""
        # System message should be first
        if self._messages and self._messages[0].role == Role.SYSTEM:
            self._messages[0].content = content
        else:
            self._messages.insert(0, Message(Role.SYSTEM, content))
    
    def update_token_usage(self, usage: TokenUsage):
        """Update with actual token usage from API."""
        self._token_usage = usage
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages as list of dicts for API."""
        return [m.to_dict() for m in self._messages]
    
    def needs_compression(self) -> bool:
        """Check if compression is needed."""
        return self.context_usage / 100 > self.compress_threshold
    
    def auto_compress(self) -> bool:
        """
        Auto-compress if threshold exceeded.
        
        Returns:
            True if compression was performed
        """
        if not self.needs_compression():
            return False
        
        self.compress()
        return True
    
    def compress(self, keep_pairs: Optional[int] = None):
        """
        Compress history by removing older messages.
        
        Args:
            keep_pairs: Number of user-assistant pairs to keep (default: preserve_recent)
        """
        keep_pairs = keep_pairs or self.preserve_recent
        
        # Find system message
        system_msg = None
        other_msgs = []
        for msg in self._messages:
            if msg.role == Role.SYSTEM:
                system_msg = msg
            else:
                other_msgs.append(msg)
        
        if len(other_msgs) <= keep_pairs * 2:
            return  # Not enough to compress
        
        # Keep last N pairs (user + assistant = 2 messages per pair)
        keep_count = keep_pairs * 2
        kept_msgs = other_msgs[-keep_count:]
        
        # Create compression notice
        removed_count = len(other_msgs) - keep_count
        compression_notice = Message(
            Role.USER,
            f"[Previous {removed_count} messages compressed to save context. Key context preserved.]"
        )
        
        # Rebuild messages
        self._messages = []
        if system_msg:
            self._messages.append(system_msg)
        self._messages.append(compression_notice)
        self._messages.extend(kept_msgs)
        
        self._compression_count += 1
        
        # Re-estimate tokens
        total_chars = sum(len(m.content) for m in self._messages)
        self._token_usage.total_tokens = total_chars // 4
    
    def crop(self, direction: CropDirection, count: int) -> int:
        """
        Crop messages from history.
        
        Args:
            direction: TOP (oldest) or BOTTOM (newest)
            count: Number of messages to remove
            
        Returns:
            Actual number of messages removed
        """
        # Find system message index
        system_idx = -1
        for i, msg in enumerate(self._messages):
            if msg.role == Role.SYSTEM:
                system_idx = i
                break
        
        if direction == CropDirection.TOP:
            # Remove from start (after system message)
            start_idx = system_idx + 1 if system_idx >= 0 else 0
            end_idx = min(start_idx + count, len(self._messages) - self.preserve_recent * 2)
            if end_idx > start_idx:
                del self._messages[start_idx:end_idx]
                return end_idx - start_idx
        else:
            # Remove from end (but keep last user message)
            # Find last user message
            last_user_idx = len(self._messages)
            for i in range(len(self._messages) - 1, -1, -1):
                if self._messages[i].role == Role.USER:
                    last_user_idx = i
                    break
            
            # Remove messages before last user (up to count)
            end_idx = last_user_idx
            start_idx = max(system_idx + 1, end_idx - count)
            if end_idx > start_idx:
                del self._messages[start_idx:end_idx]
                return end_idx - start_idx
        
        return 0
    
    def clear(self, keep_system: bool = True):
        """Clear history."""
        if keep_system:
            system_msg = None
            for msg in self._messages:
                if msg.role == Role.SYSTEM:
                    system_msg = msg
                    break
            self._messages = [system_msg] if system_msg else []
        else:
            self._messages = []
        
        self._token_usage = TokenUsage()
        self._compression_count = 0
    
    def save(self, path: str):
        """Save history to file."""
        data = {
            "messages": [m.to_dict() for m in self._messages],
            "token_usage": {
                "input": self._token_usage.input_tokens,
                "output": self._token_usage.output_tokens,
                "total": self._token_usage.total_tokens,
            },
            "compression_count": self._compression_count,
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: str) -> bool:
        """Load history from file."""
        try:
            with open(path) as f:
                data = json.load(f)
            
            self._messages = [Message.from_dict(m) for m in data.get("messages", [])]
            usage = data.get("token_usage", {})
            self._token_usage = TokenUsage(
                input_tokens=usage.get("input", 0),
                output_tokens=usage.get("output", 0),
                total_tokens=usage.get("total", 0),
            )
            self._compression_count = data.get("compression_count", 0)
            return True
        except Exception:
            return False
    
    def summary(self) -> str:
        """Get history summary."""
        msg_count = len(self._messages)
        user_count = sum(1 for m in self._messages if m.role == Role.USER)
        return (
            f"Messages: {msg_count} ({user_count} user) | "
            f"Context: {self.context_usage_str} | "
            f"Compressions: {self._compression_count}"
        )


class ContextManager:
    """
    Manages context for LLM including files, history, and environment.
    
    Builds optimal context for each request while staying within token limits.
    """
    
    def __init__(
        self,
        history: Optional[HistoryManager] = None,
        max_file_tokens: int = 50000,
        max_context_files: int = 20
    ):
        self.history = history or HistoryManager()
        self.max_file_tokens = max_file_tokens
        self.max_context_files = max_context_files
        
        self._file_context: Dict[str, str] = {}
        self._environment_context: Dict[str, str] = {}
    
    def add_file_context(self, path: str, content: str):
        """Add a file to context."""
        if len(self._file_context) >= self.max_context_files:
            # Remove oldest file
            oldest = next(iter(self._file_context))
            del self._file_context[oldest]
        
        # Truncate if too long
        max_chars = self.max_file_tokens * 4  # Rough estimate
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... [truncated]"
        
        self._file_context[path] = content
    
    def remove_file_context(self, path: str):
        """Remove a file from context."""
        self._file_context.pop(path, None)
    
    def set_environment(self, key: str, value: str):
        """Set environment context."""
        self._environment_context[key] = value
    
    def build_context(self) -> str:
        """Build full context string."""
        parts = []
        
        # Environment info
        if self._environment_context:
            parts.append("## Environment")
            for key, value in self._environment_context.items():
                parts.append(f"- {key}: {value}")
            parts.append("")
        
        # File context
        if self._file_context:
            parts.append("## Relevant Files")
            for path, content in self._file_context.items():
                parts.append(f"### {path}")
                parts.append(f"```\n{content}\n```")
            parts.append("")
        
        return "\n".join(parts)
    
    def get_file_list(self) -> List[str]:
        """Get list of files in context."""
        return list(self._file_context.keys())
    
    def clear_files(self):
        """Clear file context."""
        self._file_context.clear()


# Convenience functions
def create_history(max_tokens: int = 128000) -> HistoryManager:
    """Create a new history manager."""
    return HistoryManager(max_tokens=max_tokens)

def create_context(history: Optional[HistoryManager] = None) -> ContextManager:
    """Create a new context manager."""
    return ContextManager(history=history)
