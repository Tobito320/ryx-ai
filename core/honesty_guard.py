#!/usr/bin/env python3
"""
HONESTY GUARD - The Safety Net

Ryx must be brutally honest about its limitations.
If it's not sure, it MUST say so and NOT apply changes.
All failures are logged for learning.

Philosophy:
- Better to admit "I don't know" than to guess wrong
- Better to ask than to break code
- Every failure is a learning opportunity
- Confidence without competence is dangerous
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

# Setup failure logger
FAILURE_LOG_DIR = Path("/home/tobi/ryx-ai/data/failure_logs")
FAILURE_LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("honesty_guard")


class ConfidenceLevel(Enum):
    """How confident is Ryx about this action?"""
    CERTAIN = 4       # 95%+ sure, safe to proceed
    CONFIDENT = 3     # 80-95% sure, proceed with backup
    UNCERTAIN = 2     # 50-80% sure, ask user first
    LOST = 1          # <50% sure, admit it and don't proceed
    NO_IDEA = 0       # 0%, completely lost


@dataclass
class HonestyCheck:
    """Result of an honesty check"""
    timestamp: str
    task: str
    confidence: ConfidenceLevel
    reasoning: str
    should_proceed: bool
    should_ask_user: bool
    proposed_action: Optional[str] = None
    backup_created: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass 
class FailureLog:
    """Log entry for a failure"""
    timestamp: str
    task: str
    error_type: str
    error_message: str
    context: Dict[str, Any]
    what_ryx_tried: str
    why_it_failed: str
    what_ryx_learned: str
    confidence_was: str
    file_affected: Optional[str] = None
    changes_reverted: bool = False


class HonestyGuard:
    """
    The Safety Net - Makes Ryx brutally honest about its limitations.
    
    Rules:
    1. If confidence < 50%, DO NOT proceed. Admit it.
    2. If confidence < 80%, ASK USER first.
    3. Always create backups before changes.
    4. Log ALL failures for learning.
    5. Never pretend to know something you don't.
    """
    
    HONEST_ADMISSIONS = [
        "I'm not smart enough for this yet. Let me try to figure it out.",
        "I don't know how to do this. Can you give me more details?",
        "I'm not confident I understand. Can you clarify?",
        "I could try, but I might break something. Should I proceed?",
        "I'm stuck. Here's what I tried and why it didn't work:",
        "I failed at this. Logging it so I can learn.",
        "I don't have enough context to do this safely.",
        "I'm uncertain about this. Let me explain my hesitation:",
    ]
    
    def __init__(self):
        self.failure_log_path = FAILURE_LOG_DIR / f"failures_{datetime.now().strftime('%Y%m')}.jsonl"
        self.session_failures: List[FailureLog] = []
        self.session_uncertainties: List[HonestyCheck] = []
    
    def assess_confidence(self, task: str, context: Dict[str, Any] = None) -> HonestyCheck:
        """
        Honestly assess confidence level for a task.
        Returns HonestyCheck with recommendation.
        """
        context = context or {}
        confidence = ConfidenceLevel.UNCERTAIN
        reasoning = []
        warnings = []
        should_proceed = False
        should_ask = True
        
        task_lower = task.lower()
        
        # === CONFIDENCE BOOSTERS ===
        
        # Has specific file mentioned?
        has_file = any(ext in task_lower for ext in ['.py', '.js', '.ts', '.json', '.yaml'])
        if has_file:
            confidence = ConfidenceLevel.CONFIDENT
            reasoning.append("Specific file mentioned")
        
        # Has clear action verb?
        clear_actions = ['add', 'remove', 'delete', 'create', 'fix', 'change', 'update', 'rename']
        has_action = any(action in task_lower for action in clear_actions)
        if has_action:
            reasoning.append("Clear action verb present")
        
        # Has specific target?
        specific_targets = ['function', 'class', 'method', 'variable', 'import', 'line']
        has_target = any(target in task_lower for target in specific_targets)
        if has_target:
            reasoning.append("Specific target mentioned")
            if confidence.value < ConfidenceLevel.CONFIDENT.value:
                confidence = ConfidenceLevel.CONFIDENT
        
        # === CONFIDENCE KILLERS ===
        
        # Super vague?
        vague_words = ['it', 'this', 'that', 'thing', 'stuff', 'something']
        is_vague = any(f" {word} " in f" {task_lower} " for word in vague_words)
        if is_vague and not has_file:
            confidence = ConfidenceLevel.UNCERTAIN
            warnings.append("Vague reference without specific file")
        
        # Too short?
        if len(task.split()) < 3:
            confidence = ConfidenceLevel.LOST
            reasoning.append("Task too brief to understand")
            warnings.append("Need more context")
        
        # Dangerous operations?
        dangerous = ['delete all', 'remove all', 'drop', 'truncate', 'rm -rf', 'reset hard']
        is_dangerous = any(d in task_lower for d in dangerous)
        if is_dangerous:
            confidence = ConfidenceLevel.UNCERTAIN
            warnings.append("⚠️ DANGEROUS OPERATION - Requires explicit confirmation")
            should_ask = True
        
        # No context at all?
        if not context.get('files_found') and not context.get('current_file'):
            if not has_file:
                if confidence.value > ConfidenceLevel.UNCERTAIN.value:
                    confidence = ConfidenceLevel.UNCERTAIN
                warnings.append("No files found and none specified")
        
        # === FINAL DECISION ===
        
        if confidence == ConfidenceLevel.CERTAIN:
            should_proceed = True
            should_ask = False
        elif confidence == ConfidenceLevel.CONFIDENT:
            should_proceed = True
            should_ask = False
        elif confidence == ConfidenceLevel.UNCERTAIN:
            should_proceed = False
            should_ask = True
        else:  # LOST or NO_IDEA
            should_proceed = False
            should_ask = True
        
        return HonestyCheck(
            timestamp=datetime.now().isoformat(),
            task=task,
            confidence=confidence,
            reasoning="; ".join(reasoning) if reasoning else "No clear indicators",
            should_proceed=should_proceed,
            should_ask_user=should_ask,
            warnings=warnings
        )
    
    def admit_limitation(self, confidence: ConfidenceLevel, task: str) -> str:
        """Generate an honest admission based on confidence level."""
        
        if confidence == ConfidenceLevel.NO_IDEA:
            return f"""🤷 I have no idea how to do this.

Task: "{task}"

I don't understand what you're asking. Could you:
1. Be more specific about which file?
2. Describe what you want changed?
3. Give me an example?

I'd rather admit I'm lost than guess and break something."""

        elif confidence == ConfidenceLevel.LOST:
            return f"""😕 I'm not smart enough for this yet.

Task: "{task}"

I understand parts of it, but I'm missing context:
- Which file should I modify?
- What exactly should change?

Let me try to figure it out, or you can give me more details."""

        elif confidence == ConfidenceLevel.UNCERTAIN:
            return f"""🤔 I'm not fully confident about this.

Task: "{task}"

I think I understand, but I want to make sure before I change anything.
Can you confirm:
- Is this the right approach?
- Should I proceed?

I'd rather ask than assume."""

        else:
            return ""
    
    def log_failure(
        self,
        task: str,
        error_type: str,
        error_message: str,
        what_tried: str,
        why_failed: str,
        context: Dict[str, Any] = None,
        file_affected: str = None,
        changes_reverted: bool = False
    ) -> FailureLog:
        """Log a failure for learning."""
        
        what_learned = self._extract_learning(error_type, why_failed)
        
        failure = FailureLog(
            timestamp=datetime.now().isoformat(),
            task=task,
            error_type=error_type,
            error_message=str(error_message)[:500],
            context=context or {},
            what_ryx_tried=what_tried,
            why_it_failed=why_failed,
            what_ryx_learned=what_learned,
            confidence_was=context.get('confidence', 'unknown') if context else 'unknown',
            file_affected=file_affected,
            changes_reverted=changes_reverted
        )
        
        self.session_failures.append(failure)
        
        try:
            with open(self.failure_log_path, 'a') as f:
                f.write(json.dumps(asdict(failure)) + '\n')
            logger.info(f"Logged failure: {error_type} - {task[:50]}...")
        except Exception as e:
            logger.error(f"Failed to log failure: {e}")
        
        return failure
    
    def _extract_learning(self, error_type: str, why_failed: str) -> str:
        """Extract actionable learning from a failure."""
        
        learnings = {
            "file_not_found": "Need to verify file exists before attempting edit",
            "search_not_found": "Search text didn't match - need better fuzzy matching",
            "syntax_error": "Generated code had syntax issues - need validation",
            "permission_denied": "Don't have permission - should check first",
            "ambiguous_target": "Multiple matches found - need to ask user which one",
            "no_context": "Didn't have enough context - should ask for clarification",
            "timeout": "Operation took too long - need to break into smaller steps",
        }
        
        learning = learnings.get(error_type, "Need to analyze this failure pattern")
        
        if "not found" in why_failed.lower():
            learning += "; File or text not found - verify paths"
        if "indent" in why_failed.lower():
            learning += "; Indentation issue - be more careful with whitespace"
            
        return learning
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of session failures and uncertainties."""
        return {
            "total_failures": len(self.session_failures),
            "total_uncertainties": len(self.session_uncertainties),
            "failures": [asdict(f) for f in self.session_failures[-10:]],
            "learnings": list(set(f.what_ryx_learned for f in self.session_failures))
        }
    
    def should_abort(self, confidence: ConfidenceLevel) -> bool:
        """Should we abort this operation?"""
        return confidence in [ConfidenceLevel.LOST, ConfidenceLevel.NO_IDEA]


# Singleton instance
_guard = None

def get_honesty_guard() -> HonestyGuard:
    """Get the global HonestyGuard instance."""
    global _guard
    if _guard is None:
        _guard = HonestyGuard()
    return _guard


def log_honest_failure(task: str, error: Exception, context: dict = None) -> FailureLog:
    """Quick helper to log a failure."""
    guard = get_honesty_guard()
    return guard.log_failure(
        task=task,
        error_type=type(error).__name__,
        error_message=str(error),
        what_tried=task,
        why_failed=str(error),
        context=context or {}
    )


def check_confidence(task: str, context: dict = None) -> Tuple[bool, Optional[str]]:
    """Quick helper to check confidence. Returns (should_proceed, message)"""
    guard = get_honesty_guard()
    check = guard.assess_confidence(task, context or {})
    
    if check.should_proceed:
        return True, None
    else:
        return False, guard.admit_limitation(check.confidence, task)


if __name__ == "__main__":
    guard = HonestyGuard()
    
    print("="*70)
    print("  HONESTY GUARD - TESTING")
    print("="*70)
    
    test_cases = [
        ("fix it", {}),
        ("add logging to main.py", {"files_found": ["main.py"]}),
        ("delete all files", {}),
        ("x", {}),
        ("update the authentication in src/auth.py", {"files_found": ["src/auth.py"]}),
    ]
    
    for task, context in test_cases:
        print(f"\nTask: '{task}'")
        check = guard.assess_confidence(task, context)
        print(f"  Confidence: {check.confidence.name}")
        print(f"  Should proceed: {check.should_proceed}")
        if not check.should_proceed:
            print(f"  Admission: {guard.admit_limitation(check.confidence, task)[:80]}...")
    
    print("\n✅ Honesty Guard working!")


def check_confidence(task: str, context: dict = None):
    """Quick helper to check confidence. Returns (should_proceed, message)"""
    guard = get_honesty_guard()
    check = guard.assess_confidence(task, context or {})
    
    if check.should_proceed:
        return True, None
    else:
        return False, guard.admit_limitation(check.confidence, task)
