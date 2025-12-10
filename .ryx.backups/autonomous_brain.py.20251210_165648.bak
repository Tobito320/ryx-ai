"""
Autonomous Brain for Ryx AI - Inspired by Jarvis

Core principle: PREDICT → DECIDE → ACT (no confirmations)

Key features from research:
- Confidence-based autonomy (from Aider)
- Self-healing error recovery (from healing-agent)
- User persona modeling (from MemGPT concept)
- Reflection loops (from SelfImprovingAgent)
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.paths import get_data_dir
from core.model_detector import get_detector

logger = logging.getLogger(__name__)


@dataclass
class UserPersona:
    """User profile - learns over time"""
    preferences: Dict[str, Any] = field(default_factory=dict)
    coding_style: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, int] = field(default_factory=dict)  # Action → count
    approval_threshold: float = 0.7  # Lower = more autonomous
    last_updated: str = ""
    
    def record_action(self, action: str, approved: bool = True):
        """Learn from user's response"""
        if approved:
            self.patterns[action] = self.patterns.get(action, 0) + 1
            # Gradually lower threshold as trust builds
            if self.patterns[action] > 10:
                self.approval_threshold = max(0.5, self.approval_threshold - 0.01)
    
    def should_ask_permission(self, action: str, confidence: float) -> bool:
        """Decide if we need permission for this action"""
        # High confidence + familiar pattern = just do it
        if confidence >= 0.9:
            return False
        
        # We've done this successfully many times
        if self.patterns.get(action, 0) > 5:
            return False
        
        # Below threshold
        return confidence < self.approval_threshold


@dataclass
class ActionPlan:
    """A plan with confidence score"""
    action: str
    intent: str
    target: Optional[str]
    steps: list = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    risks: list = field(default_factory=list)


class AutonomousBrain:
    """
    Enhanced brain that acts autonomously.
    
    Philosophy:
    - Trust by default
    - Learn from mistakes
    - Never ask permission unless genuinely uncertain
    """
    
    def __init__(self, base_brain):
        """Wraps the existing RyxBrain with autonomous capabilities"""
        self.brain = base_brain
        self.persona = self._load_persona()
        self.detector = get_detector()
        self.error_memory: list = []  # Remember past errors
        self.max_retries = 3
        
    def _load_persona(self) -> UserPersona:
        """Load user persona from disk"""
        persona_file = get_data_dir() / "user_persona.json"
        if persona_file.exists():
            try:
                data = json.loads(persona_file.read_text())
                return UserPersona(**data)
            except:
                pass
        return UserPersona()
    
    def _save_persona(self):
        """Save persona to disk"""
        persona_file = get_data_dir() / "user_persona.json"
        persona_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "preferences": self.persona.preferences,
            "coding_style": self.persona.coding_style,
            "patterns": self.persona.patterns,
            "approval_threshold": self.persona.approval_threshold,
            "last_updated": datetime.now().isoformat()
        }
        persona_file.write_text(json.dumps(data, indent=2))
    
    def understand_with_confidence(self, prompt: str) -> Tuple[Any, float]:
        """
        Enhanced understanding that includes confidence scoring.
        
        Returns:
            (Plan, confidence_score)
        """
        # Get base plan from brain
        plan = self.brain.understand(prompt)
        
        # Calculate confidence based on:
        # 1. Cache hit (high confidence)
        # 2. Known patterns (medium confidence)
        # 3. Clear intent keywords (medium confidence)
        # 4. Ambiguous/complex (low confidence)
        
        confidence = 0.5  # Base confidence
        
        # Cache hit = we've done this before successfully
        cached = self.brain.cache.lookup(prompt)
        if cached:
            confidence = 0.95
        
        # Pattern match
        action_type = plan.intent.value
        if self.persona.patterns.get(action_type, 0) > 3:
            confidence += 0.2
        
        # Clear keywords
        clear_keywords = [
            'open', 'create', 'add', 'fix', 'update', 
            'delete', 'search', 'find'
        ]
        if any(kw in prompt.lower() for kw in clear_keywords):
            confidence += 0.15
        
        # File paths or URLs = specific target = higher confidence
        if plan.target:
            confidence += 0.15
        
        # Cap at 1.0
        confidence = min(confidence, 1.0)
        
        return plan, confidence
    
    def execute_autonomously(self, plan: Any, confidence: float) -> Tuple[bool, str]:
        """
        Execute with self-healing retry logic.
        
        Returns:
            (success, result)
        """
        action_type = plan.intent.value
        
        # Check if we should ask permission
        if self.persona.should_ask_permission(action_type, confidence):
            # TODO: Implement async permission request
            # For now, just proceed with caution
            logger.info(f"Low confidence ({confidence:.2f}) but proceeding")
        
        # Execute with retry loop
        for attempt in range(self.max_retries):
            try:
                success, result = self.brain.execute(plan)
                
                if success:
                    # Learn from success
                    self.persona.record_action(action_type, approved=True)
                    self._save_persona()
                    return True, result
                
                # Failed - try to heal
                if attempt < self.max_retries - 1:
                    logger.info(f"Attempt {attempt + 1} failed, reflecting...")
                    plan = self._reflect_and_improve(plan, result)
                else:
                    return False, result
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    return False, str(e)
        
        return False, "Max retries exceeded"
    
    def _reflect_and_improve(self, plan: Any, error: str) -> Any:
        """
        Reflect on failure and generate improved plan.
        
        Inspired by self-improving agent pattern.
        """
        # Analyze what went wrong
        reflection = self._analyze_error(error)
        
        # Store in error memory
        self.error_memory.append({
            "plan": str(plan),
            "error": error,
            "reflection": reflection,
            "timestamp": datetime.now().isoformat()
        })
        
        # Adjust plan based on reflection
        # For now, just return original (brain will try with same plan)
        # TODO: Use LLM to generate improved plan
        
        return plan
    
    def _analyze_error(self, error: str) -> str:
        """Analyze why the error occurred"""
        error_lower = error.lower()
        
        if "file not found" in error_lower or "no such file" in error_lower:
            return "TARGET_NOT_FOUND: File path was incorrect or doesn't exist"
        elif "permission denied" in error_lower:
            return "PERMISSION_DENIED: Need elevated permissions"
        elif "404" in error_lower or "not found" in error_lower:
            return "HTTP_404: URL or API endpoint not accessible"
        elif "syntax error" in error_lower or "invalid syntax" in error_lower:
            return "SYNTAX_ERROR: Generated code has syntax issues"
        elif "timeout" in error_lower:
            return "TIMEOUT: Operation took too long"
        else:
            return f"UNKNOWN_ERROR: {error[:100]}"
    
    def learn_from_feedback(self, prompt: str, plan: Any, approved: bool):
        """Learn from user feedback on actions"""
        action_type = plan.intent.value
        self.persona.record_action(action_type, approved)
        self._save_persona()
    
    def predict_intent(self, partial_prompt: str) -> Optional[str]:
        """
        Predict what the user wants (Jarvis-style).
        
        Based on:
        - Recent patterns
        - Time of day
        - Common sequences
        """
        # Find most common recent actions
        if not self.persona.patterns:
            return None
        
        # Get top 3 most frequent actions
        sorted_patterns = sorted(
            self.persona.patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        if sorted_patterns:
            top_action = sorted_patterns[0][0]
            # Check if partial prompt matches
            if any(word in partial_prompt.lower() for word in top_action.split('_')):
                return f"Predicted: {top_action}"
        
        return None


def get_autonomous_brain(base_brain) -> AutonomousBrain:
    """Create autonomous wrapper around base brain"""
    return AutonomousBrain(base_brain)
