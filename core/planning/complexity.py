"""
Ryx AI - Complexity Gate

Rule-based complexity classification to decide whether supervisor planning is needed.
No LLM calls - uses pattern matching for speed.
"""

import re
from typing import Optional, Tuple
from .schemas import TaskComplexity, AgentType


class ComplexityGate:
    """
    Classifies task complexity to route to appropriate handler.
    
    Routing:
    - TRIVIAL: Direct tool execution (no LLM)
    - SIMPLE: Small operator only (3B)
    - MODERATE: Supervisor planning + operator
    - COMPLEX: Full supervisor + larger operator (7B+)
    """
    
    # Patterns for trivial tasks (no LLM needed)
    TRIVIAL_PATTERNS = {
        "website": [
            r"^open\s+(youtube|github|google|reddit|twitter|x\.com|stackoverflow)",
            r"^öffne\s+(youtube|github|google|reddit|twitter)",
            r"^go\s+to\s+(youtube|github|google)",
        ],
        "time": [
            r"^(what\s+)?(time|date|day)",
            r"^(wie\s+)?(spät|uhrzeit|datum|tag)",
        ],
        "quit": [
            r"^(quit|exit|bye|q)$",
            r"^(beenden|tschüss)$",
        ],
    }
    
    # Patterns for simple tasks (single tool, small LLM)
    SIMPLE_PATTERNS = {
        "file_find": [
            r"^find\s+\S+",
            r"^finde\s+\S+",
            r"^where\s+is\s+\S+",
            r"^wo\s+ist\s+\S+",
            r"^locate\s+\S+",
        ],
        "file_open": [
            r"^open\s+.*config",
            r"^öffne\s+.*config",
            r"^edit\s+\S+",
            r"^bearbeite\s+\S+",
        ],
        "git_simple": [
            r"^git\s+status",
            r"^git\s+diff",
            r"^git\s+log",
        ],
    }
    
    # Patterns for complex tasks (reasoning, large LLM)
    COMPLEX_PATTERNS = {
        "refactor": [
            r"refactor",
            r"rewrite",
            r"improve.*code",
            r"optimize",
            r"umschreiben",
            r"verbessern",
        ],
        "create": [
            r"create\s+(a\s+)?(new\s+)?(file|script|module|class|function)",
            r"erstelle",
            r"schreibe.*code",
            r"write\s+(a\s+)?(new\s+)?",
        ],
        "explain": [
            r"explain\s+(how|why|what)",
            r"erkläre",
            r"how\s+does.*work",
            r"why\s+does",
        ],
        "analyze": [
            r"analyze",
            r"review",
            r"check\s+for\s+(errors|bugs|issues)",
            r"debug",
            r"analysiere",
        ],
    }
    
    def classify(self, query: str) -> Tuple[TaskComplexity, Optional[AgentType]]:
        """
        Classify query complexity and suggest agent type.
        
        Returns:
            (complexity, agent_type) - agent_type may be None for trivial tasks
        """
        q = query.lower().strip()
        
        # Check trivial patterns first (fastest path)
        for category, patterns in self.TRIVIAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q):
                    return TaskComplexity.TRIVIAL, self._agent_for_trivial(category)
        
        # Check complex patterns (needs supervisor)
        for category, patterns in self.COMPLEX_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q):
                    return TaskComplexity.COMPLEX, self._agent_for_complex(category)
        
        # Check simple patterns
        for category, patterns in self.SIMPLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q):
                    return TaskComplexity.SIMPLE, self._agent_for_simple(category)
        
        # Check for multiple entities/steps (moderate)
        if self._has_multiple_targets(q):
            return TaskComplexity.MODERATE, AgentType.SHELL
        
        # Default: moderate (let supervisor decide)
        return TaskComplexity.MODERATE, None
    
    def _agent_for_trivial(self, category: str) -> Optional[AgentType]:
        """Get agent type for trivial task category"""
        mapping = {
            "website": AgentType.WEB,
            "time": None,  # Direct execution
            "quit": None,
        }
        return mapping.get(category)
    
    def _agent_for_simple(self, category: str) -> AgentType:
        """Get agent type for simple task category"""
        mapping = {
            "file_find": AgentType.FILE,
            "file_open": AgentType.FILE,
            "git_simple": AgentType.SHELL,
        }
        return mapping.get(category, AgentType.SHELL)
    
    def _agent_for_complex(self, category: str) -> AgentType:
        """Get agent type for complex task category"""
        mapping = {
            "refactor": AgentType.CODE,
            "create": AgentType.CODE,
            "explain": AgentType.RAG,
            "analyze": AgentType.CODE,
        }
        return mapping.get(category, AgentType.CODE)
    
    def _has_multiple_targets(self, query: str) -> bool:
        """Check if query mentions multiple files/targets"""
        # Multiple files mentioned
        file_mentions = len(re.findall(r'\b\w+\.(py|js|ts|json|yaml|md|txt|sh|conf)\b', query))
        if file_mentions > 1:
            return True
        
        # Multiple actions (and/then/also)
        if re.search(r'\b(and|then|also|und|dann|auch)\b', query):
            return True
        
        # List of items
        if re.search(r'\d+\.\s+\w+', query):  # "1. do this 2. do that"
            return True
        
        return False
    
    def should_skip_supervisor(self, complexity: TaskComplexity) -> bool:
        """Check if we can skip supervisor for this complexity"""
        return complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]


# Singleton instance
_gate: Optional[ComplexityGate] = None

def get_complexity_gate() -> ComplexityGate:
    """Get singleton complexity gate instance"""
    global _gate
    if _gate is None:
        _gate = ComplexityGate()
    return _gate
