"""
Ryx AI - Experience Memory

Stores and retrieves past experiences for learning.
Enables Ryx to:
1. Remember what worked before
2. Remember what failed
3. Find similar past problems
4. Learn from patterns

This is key for the RSI loop - each attempt creates an experience
that informs future attempts.
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ExperienceType(Enum):
    """Type of experience"""
    SUCCESS = "success"       # Task completed successfully
    FAILURE = "failure"       # Task failed
    PARTIAL = "partial"       # Partial success
    FIXED = "fixed"           # Error was fixed
    LEARNED = "learned"       # Pattern learned


@dataclass
class Experience:
    """A single experience/memory"""
    
    experience_id: str
    experience_type: ExperienceType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # The task
    task_description: str = ""
    task_category: str = ""
    
    # What happened
    approach_taken: str = ""
    result: str = ""
    error_if_any: Optional[str] = None
    
    # The fix (if applicable)
    fix_applied: Optional[str] = None
    fix_explanation: Optional[str] = None
    
    # Metrics
    score: float = 0.0
    tokens_used: int = 0
    time_seconds: float = 0.0
    
    # For retrieval
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['experience_type'] = self.experience_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Experience':
        d['experience_type'] = ExperienceType(d['experience_type'])
        return cls(**d)
    
    def summary(self) -> str:
        """Short summary for display"""
        status = "✓" if self.experience_type == ExperienceType.SUCCESS else "✗"
        return f"{status} [{self.task_category}] {self.task_description[:50]}..."


@dataclass
class PatternMatch:
    """A matched pattern from experience"""
    experience: Experience
    similarity: float
    relevant_insight: str


class ExperienceMemory:
    """
    Stores and retrieves experiences.
    
    Usage:
        memory = ExperienceMemory()
        
        # Store a success
        memory.store_success(
            task="Write fibonacci function",
            approach="Used dynamic programming",
            result="def fibonacci(n): ...",
            tags=["algorithm", "recursion"]
        )
        
        # Store a failure
        memory.store_failure(
            task="Parse malformed JSON",
            error="JSONDecodeError",
            approach="Direct json.loads()",
            tags=["json", "parsing"]
        )
        
        # Find similar experiences
        matches = memory.find_similar("Write a recursive function")
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            self.storage_path = Path.home() / "ryx-ai" / "data" / "memory"
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._experiences: Dict[str, Experience] = {}
        self._loaded = False
        
        # Load existing experiences
        self._load_all()
    
    def _generate_id(self, task: str) -> str:
        """Generate a unique experience ID"""
        content = f"{task}{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _load_all(self):
        """Load all experiences from disk"""
        if self._loaded:
            return
        
        experiences_file = self.storage_path / "experiences.jsonl"
        if experiences_file.exists():
            try:
                with open(experiences_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            exp = Experience.from_dict(data)
                            self._experiences[exp.experience_id] = exp
                logger.info(f"Loaded {len(self._experiences)} experiences")
            except Exception as e:
                logger.error(f"Failed to load experiences: {e}")
        
        self._loaded = True
    
    def _save_experience(self, experience: Experience):
        """Append experience to storage"""
        experiences_file = self.storage_path / "experiences.jsonl"
        try:
            with open(experiences_file, 'a') as f:
                f.write(json.dumps(experience.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to save experience: {e}")
    
    def store(
        self,
        exp_type: ExperienceType,
        task: str,
        approach: str = "",
        result: str = "",
        error: Optional[str] = None,
        fix: Optional[str] = None,
        fix_explanation: Optional[str] = None,
        score: float = 0.0,
        tokens: int = 0,
        time: float = 0.0,
        category: str = "",
        tags: Optional[List[str]] = None,
    ) -> Experience:
        """Store a new experience"""
        
        exp = Experience(
            experience_id=self._generate_id(task),
            experience_type=exp_type,
            task_description=task,
            task_category=category,
            approach_taken=approach,
            result=result,
            error_if_any=error,
            fix_applied=fix,
            fix_explanation=fix_explanation,
            score=score,
            tokens_used=tokens,
            time_seconds=time,
            tags=tags or [],
        )
        
        self._experiences[exp.experience_id] = exp
        self._save_experience(exp)
        
        logger.debug(f"Stored experience: {exp.experience_id}")
        return exp
    
    def store_success(
        self,
        task: str,
        approach: str,
        result: str,
        score: float = 1.0,
        **kwargs
    ) -> Experience:
        """Convenience: store a successful experience"""
        return self.store(
            exp_type=ExperienceType.SUCCESS,
            task=task,
            approach=approach,
            result=result,
            score=score,
            **kwargs
        )
    
    def store_failure(
        self,
        task: str,
        error: str,
        approach: str = "",
        **kwargs
    ) -> Experience:
        """Convenience: store a failed experience"""
        return self.store(
            exp_type=ExperienceType.FAILURE,
            task=task,
            approach=approach,
            error=error,
            score=0.0,
            **kwargs
        )
    
    def store_fix(
        self,
        task: str,
        original_error: str,
        fix: str,
        fix_explanation: str,
        **kwargs
    ) -> Experience:
        """Convenience: store a fix experience"""
        return self.store(
            exp_type=ExperienceType.FIXED,
            task=task,
            error=original_error,
            fix=fix,
            fix_explanation=fix_explanation,
            **kwargs
        )
    
    def get(self, experience_id: str) -> Optional[Experience]:
        """Get an experience by ID"""
        return self._experiences.get(experience_id)
    
    def find_similar(
        self,
        query: str,
        limit: int = 5,
        exp_type: Optional[ExperienceType] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PatternMatch]:
        """
        Find experiences similar to a query.
        
        For now uses simple keyword matching.
        TODO: Add embedding-based search.
        """
        matches = []
        query_words = set(query.lower().split())
        
        for exp in self._experiences.values():
            # Filter by type/category/tags
            if exp_type and exp.experience_type != exp_type:
                continue
            if category and exp.task_category != category:
                continue
            if tags and not any(t in exp.tags for t in tags):
                continue
            
            # Calculate similarity (simple word overlap)
            exp_words = set(exp.task_description.lower().split())
            exp_words.update(exp.approach_taken.lower().split())
            
            if not exp_words:
                continue
            
            overlap = len(query_words & exp_words)
            similarity = overlap / max(len(query_words), len(exp_words))
            
            if similarity > 0.1:  # Threshold
                insight = self._extract_insight(exp, query)
                matches.append(PatternMatch(
                    experience=exp,
                    similarity=similarity,
                    relevant_insight=insight
                ))
        
        # Sort by similarity
        matches.sort(key=lambda m: m.similarity, reverse=True)
        
        return matches[:limit]
    
    def _extract_insight(self, exp: Experience, query: str) -> str:
        """Extract relevant insight from an experience"""
        if exp.experience_type == ExperienceType.SUCCESS:
            return f"Previously worked: {exp.approach_taken[:100]}"
        elif exp.experience_type == ExperienceType.FAILURE:
            return f"Previously failed with: {exp.error_if_any}"
        elif exp.experience_type == ExperienceType.FIXED:
            return f"Fixed by: {exp.fix_explanation or exp.fix_applied[:100]}"
        return ""
    
    def get_successes(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Experience]:
        """Get successful experiences"""
        results = []
        for exp in self._experiences.values():
            if exp.experience_type != ExperienceType.SUCCESS:
                continue
            if category and exp.task_category != category:
                continue
            results.append(exp)
        
        # Sort by score, then by recency
        results.sort(key=lambda e: (e.score, e.timestamp), reverse=True)
        return results[:limit]
    
    def get_failures(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Experience]:
        """Get failed experiences (to avoid repeating)"""
        results = []
        for exp in self._experiences.values():
            if exp.experience_type != ExperienceType.FAILURE:
                continue
            if category and exp.task_category != category:
                continue
            results.append(exp)
        
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]
    
    def get_fixes(self, limit: int = 10) -> List[Experience]:
        """Get fix experiences (for self-healing)"""
        results = [
            exp for exp in self._experiences.values()
            if exp.experience_type == ExperienceType.FIXED
        ]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored experiences"""
        stats = {
            "total": len(self._experiences),
            "by_type": {},
            "by_category": {},
            "success_rate": 0.0,
        }
        
        successes = 0
        for exp in self._experiences.values():
            # By type
            type_name = exp.experience_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            # By category
            if exp.task_category:
                stats["by_category"][exp.task_category] = \
                    stats["by_category"].get(exp.task_category, 0) + 1
            
            if exp.experience_type == ExperienceType.SUCCESS:
                successes += 1
        
        if stats["total"] > 0:
            stats["success_rate"] = successes / stats["total"]
        
        return stats
    
    def clear(self):
        """Clear all experiences (use with caution!)"""
        self._experiences.clear()
        experiences_file = self.storage_path / "experiences.jsonl"
        if experiences_file.exists():
            experiences_file.unlink()
        logger.warning("Cleared all experiences")


# Global instance
_memory: Optional[ExperienceMemory] = None


def get_memory() -> ExperienceMemory:
    """Get or create the global experience memory"""
    global _memory
    if _memory is None:
        _memory = ExperienceMemory()
    return _memory
