"""
Ryx AI - Tool Schema

JSON Schema definitions for structured tool calls.
Ensures LLM outputs only valid tool calls, not free text.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ToolCallType(Enum):
    """Types of tool calls"""
    READ = "read"           # Read-only operations
    WRITE = "write"         # File modifications
    EXECUTE = "execute"     # Command execution
    SEARCH = "search"       # Search operations
    GIT = "git"             # Git operations
    COMPLETE = "complete"   # Task completion signal


@dataclass
class ToolCall:
    """A structured tool call from LLM"""
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "tool": self.tool,
            "params": self.params,
            "reasoning": self.reasoning
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ToolCall':
        return cls(
            tool=data.get("tool", ""),
            params=data.get("params", {}),
            reasoning=data.get("reasoning", "")
        )


@dataclass
class ToolCallSequence:
    """A sequence of tool calls"""
    calls: List[ToolCall] = field(default_factory=list)
    complete: bool = False
    final_message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "calls": [c.to_dict() for c in self.calls],
            "complete": self.complete,
            "final_message": self.final_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ToolCallSequence':
        return cls(
            calls=[ToolCall.from_dict(c) for c in data.get("calls", [])],
            complete=data.get("complete", False),
            final_message=data.get("final_message", "")
        )


# JSON Schema for tool calls
TOOL_CALL_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {
            "type": "string",
            "description": "Name of the tool to execute",
            "enum": [
                "read_file",
                "list_directory", 
                "search_code",
                "write_file",
                "apply_diff",
                "search_replace",
                "create_file",
                "delete_file",
                "run_command",
                "git_status",
                "git_commit",
                "git_diff",
                "find_relevant_files",
                "complete"
            ]
        },
        "params": {
            "type": "object",
            "description": "Parameters for the tool"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this tool is being called"
        }
    },
    "required": ["tool"]
}

# Tool-specific parameter schemas
TOOL_PARAMS = {
    "read_file": {
        "path": {"type": "string", "required": True},
        "start_line": {"type": "integer", "required": False},
        "end_line": {"type": "integer", "required": False}
    },
    "list_directory": {
        "path": {"type": "string", "required": False, "default": "."},
        "max_depth": {"type": "integer", "required": False, "default": 2}
    },
    "search_code": {
        "pattern": {"type": "string", "required": True},
        "path": {"type": "string", "required": False, "default": "."},
        "file_pattern": {"type": "string", "required": False}
    },
    "write_file": {
        "path": {"type": "string", "required": True},
        "content": {"type": "string", "required": True}
    },
    "apply_diff": {
        "path": {"type": "string", "required": True},
        "diff": {"type": "string", "required": True}
    },
    "search_replace": {
        "path": {"type": "string", "required": True},
        "search": {"type": "string", "required": True},
        "replace": {"type": "string", "required": True},
        "all_occurrences": {"type": "boolean", "required": False, "default": False}
    },
    "create_file": {
        "path": {"type": "string", "required": True},
        "content": {"type": "string", "required": True}
    },
    "delete_file": {
        "path": {"type": "string", "required": True}
    },
    "run_command": {
        "command": {"type": "string", "required": True},
        "timeout": {"type": "integer", "required": False, "default": 30}
    },
    "git_status": {},
    "git_commit": {
        "message": {"type": "string", "required": True},
        "files": {"type": "array", "required": False}
    },
    "git_diff": {
        "files": {"type": "array", "required": False}
    },
    "find_relevant_files": {
        "query": {"type": "string", "required": True},
        "max_files": {"type": "integer", "required": False, "default": 10}
    },
    "complete": {
        "message": {"type": "string", "required": True}
    }
}


class ToolCallParser:
    """Parse LLM responses into structured tool calls"""
    
    def __init__(self):
        self.valid_tools = set(TOOL_PARAMS.keys())
    
    def parse(self, response: str) -> Optional[ToolCallSequence]:
        """
        Parse LLM response into tool calls.
        
        Supports formats:
        1. Single JSON object: {"tool": "...", "params": {...}}
        2. JSON array: [{"tool": "...", ...}, ...]
        3. JSON with calls array: {"calls": [...]}
        4. Markdown code block with JSON
        
        Returns:
            ToolCallSequence if valid, None if parsing fails
        """
        response = response.strip()
        
        # Try to extract JSON from markdown code blocks
        if "```" in response:
            response = self._extract_json_from_markdown(response)
        
        # Try parsing
        try:
            data = json.loads(response)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        json_match = self._find_json(response)
        if json_match:
            try:
                data = json.loads(json_match)
                return self._parse_json(data)
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Failed to parse tool call: {response[:100]}...")
        return None
    
    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON from markdown code blocks"""
        import re
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
    
    def _find_json(self, text: str) -> Optional[str]:
        """Find JSON object or array in text"""
        import re
        
        # Find {...} or [...]
        patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested objects
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Nested arrays
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(0)
        
        return None
    
    def _parse_json(self, data: Union[Dict, List]) -> ToolCallSequence:
        """Parse JSON data into ToolCallSequence"""
        sequence = ToolCallSequence()
        
        if isinstance(data, list):
            # Array of tool calls
            for item in data:
                call = self._parse_single_call(item)
                if call:
                    sequence.calls.append(call)
        elif isinstance(data, dict):
            if "calls" in data:
                # {"calls": [...], "complete": bool, "final_message": str}
                for item in data.get("calls", []):
                    call = self._parse_single_call(item)
                    if call:
                        sequence.calls.append(call)
                sequence.complete = data.get("complete", False)
                sequence.final_message = data.get("final_message", "")
            elif "tool" in data:
                # Single tool call
                call = self._parse_single_call(data)
                if call:
                    sequence.calls.append(call)
                    if call.tool == "complete":
                        sequence.complete = True
                        sequence.final_message = call.params.get("message", "")
        
        return sequence
    
    def _parse_single_call(self, data: Dict) -> Optional[ToolCall]:
        """Parse a single tool call"""
        if not isinstance(data, dict):
            return None
        
        tool = data.get("tool", "")
        
        if not tool:
            return None
        
        # Normalize tool name
        tool = tool.lower().replace("-", "_").replace(" ", "_")
        
        if tool not in self.valid_tools:
            logger.warning(f"Unknown tool: {tool}")
            # Still return it, let the executor handle the error
        
        return ToolCall(
            tool=tool,
            params=data.get("params", data.get("parameters", {})),
            reasoning=data.get("reasoning", data.get("reason", ""))
        )
    
    def validate_call(self, call: ToolCall) -> tuple[bool, str]:
        """
        Validate a tool call against its schema.
        
        Returns:
            (is_valid, error_message)
        """
        if call.tool not in TOOL_PARAMS:
            return False, f"Unknown tool: {call.tool}"
        
        schema = TOOL_PARAMS[call.tool]
        
        # Check required params
        for param, spec in schema.items():
            if spec.get("required", False) and param not in call.params:
                return False, f"Missing required parameter: {param}"
        
        return True, ""


# System prompt for tool-only mode
TOOL_ONLY_SYSTEM_PROMPT = """You are Ryx AI, an intelligent coding assistant.

CRITICAL: You MUST respond ONLY with valid JSON tool calls. NO free text, NO explanations outside JSON.

Available tools:
- read_file: Read file contents. Params: path, start_line?, end_line?
- list_directory: List directory. Params: path?, max_depth?
- search_code: Search for patterns. Params: pattern, path?, file_pattern?
- write_file: Write entire file. Params: path, content
- apply_diff: Apply unified diff. Params: path, diff
- search_replace: Find and replace. Params: path, search, replace, all_occurrences?
- create_file: Create new file. Params: path, content
- delete_file: Delete file. Params: path
- run_command: Run shell command. Params: command, timeout?
- git_status: Get git status. No params.
- git_commit: Commit changes. Params: message, files?
- find_relevant_files: Find files for task. Params: query, max_files?
- complete: Signal task completion. Params: message

Response format (MUST be valid JSON):
{
    "tool": "tool_name",
    "params": {"param1": "value1"},
    "reasoning": "Brief reason for this action"
}

For multiple actions:
{
    "calls": [
        {"tool": "read_file", "params": {"path": "file.py"}, "reasoning": "Read to understand"},
        {"tool": "apply_diff", "params": {"path": "file.py", "diff": "..."}, "reasoning": "Fix bug"}
    ],
    "complete": false
}

When done:
{"tool": "complete", "params": {"message": "Task completed: description of what was done"}}

REMEMBER: Output ONLY valid JSON. No markdown, no explanations, no apologies."""


def get_tool_prompt(task: str, context: str = "", available_files: List[str] = None) -> str:
    """Generate a prompt for tool-only mode"""
    prompt = f"Task: {task}\n"
    
    if context:
        prompt += f"\nContext:\n{context}\n"
    
    if available_files:
        prompt += f"\nAvailable files:\n"
        for f in available_files[:20]:
            prompt += f"  - {f}\n"
    
    prompt += "\nRespond with JSON tool call(s) to accomplish this task."
    
    return prompt


# Singleton parser
_parser: Optional[ToolCallParser] = None

def get_parser() -> ToolCallParser:
    """Get or create tool call parser"""
    global _parser
    if _parser is None:
        _parser = ToolCallParser()
    return _parser
