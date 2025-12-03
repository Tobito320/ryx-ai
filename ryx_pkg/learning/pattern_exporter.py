"""
Ryx AI - Pattern Exporter

Export and import learned patterns for sharing and backup.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A learned pattern from successful resolutions"""
    id: str
    name: str
    description: str
    
    # Pattern definition
    trigger: str  # What triggers this pattern (error, task type, etc.)
    solution_template: str
    
    # Context
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    
    # Actions
    tools_sequence: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    
    # Stats
    success_count: int = 0
    confidence: float = 0.5
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "learned"  # learned, imported, user-defined


class PatternExporter:
    """
    Export and import learned patterns.
    
    Patterns can be:
    - Exported for backup
    - Shared between Ryx instances
    - Published to a pattern library
    
    Usage:
    ```python
    exporter = PatternExporter()
    
    # Export patterns
    patterns = exporter.export_patterns()
    exporter.save_to_file("patterns.json", patterns)
    
    # Import patterns
    patterns = exporter.load_from_file("patterns.json")
    exporter.import_patterns(patterns)
    ```
    """
    
    def __init__(
        self,
        resolution_tracker = None,
        preference_learner = None
    ):
        self.tracker = resolution_tracker
        self.preferences = preference_learner
        self._patterns: List[LearnedPattern] = []
    
    def extract_patterns(
        self,
        min_occurrences: int = 3,
        min_confidence: float = 0.6
    ) -> List[LearnedPattern]:
        """
        Extract patterns from resolution history.
        
        Looks for repeated successful resolution patterns.
        """
        if not self.tracker:
            return []
        
        patterns = []
        
        # Get top patterns from tracker
        top_patterns = self.tracker.get_top_patterns(limit=50)
        
        for p in top_patterns:
            if p["count"] >= min_occurrences and p["confidence"] >= min_confidence:
                pattern = LearnedPattern(
                    id=self._generate_id(p["pattern"]),
                    name=self._extract_name(p["pattern"]),
                    description=p["pattern"],
                    trigger="task",
                    solution_template=p["pattern"],
                    tools_sequence=p["tools"],
                    success_count=p["count"],
                    confidence=p["confidence"],
                    source="learned"
                )
                patterns.append(pattern)
        
        self._patterns = patterns
        return patterns
    
    def export_patterns(
        self,
        include_preferences: bool = True
    ) -> Dict[str, Any]:
        """Export all patterns and optionally preferences"""
        export_data = {
            "version": 1,
            "exported_at": datetime.now().isoformat(),
            "source": "ryx-ai",
            "patterns": [
                self._pattern_to_dict(p) for p in self._patterns
            ]
        }
        
        if include_preferences and self.preferences:
            export_data["preferences"] = self.preferences.export()
        
        return export_data
    
    def import_patterns(
        self,
        data: Dict[str, Any],
        merge: bool = True
    ) -> int:
        """
        Import patterns from exported data.
        
        Returns number of patterns imported.
        """
        imported = 0
        
        for p_data in data.get("patterns", []):
            pattern = self._dict_to_pattern(p_data)
            pattern.source = "imported"
            
            if merge:
                # Check for existing
                existing = next(
                    (p for p in self._patterns if p.id == pattern.id),
                    None
                )
                if existing:
                    # Merge stats
                    existing.success_count += pattern.success_count
                    existing.confidence = max(existing.confidence, pattern.confidence)
                    continue
            
            self._patterns.append(pattern)
            imported += 1
        
        # Import preferences if present
        if "preferences" in data and self.preferences:
            self.preferences.import_preferences(data["preferences"])
        
        return imported
    
    def save_to_file(self, path: Path, data: Optional[Dict] = None):
        """Save patterns to file"""
        path = Path(path)
        
        if data is None:
            data = self.export_patterns()
        
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.info(f"Saved patterns to {path}")
    
    def load_from_file(self, path: Path) -> Dict[str, Any]:
        """Load patterns from file"""
        path = Path(path)
        
        if not path.exists():
            return {"patterns": []}
        
        return json.loads(path.read_text())
    
    def get_matching_patterns(
        self,
        task: str,
        language: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[LearnedPattern]:
        """Find patterns matching a task"""
        matches = []
        
        task_lower = task.lower()
        task_words = set(task_lower.split())
        
        for pattern in self._patterns:
            # Check trigger match
            trigger_words = set(pattern.trigger.lower().split())
            overlap = len(task_words & trigger_words)
            
            if overlap == 0:
                continue
            
            # Check language/framework if specified
            if language and pattern.languages:
                if language not in pattern.languages:
                    continue
            
            if framework and pattern.frameworks:
                if framework not in pattern.frameworks:
                    continue
            
            matches.append(pattern)
        
        # Sort by relevance and confidence
        matches.sort(
            key=lambda p: (p.confidence, p.success_count),
            reverse=True
        )
        
        return matches[:5]
    
    def add_pattern(self, pattern: LearnedPattern):
        """Manually add a pattern"""
        pattern.source = "user-defined"
        self._patterns.append(pattern)
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern"""
        for i, p in enumerate(self._patterns):
            if p.id == pattern_id:
                del self._patterns[i]
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pattern statistics"""
        by_source = {}
        total_success = 0
        
        for p in self._patterns:
            by_source[p.source] = by_source.get(p.source, 0) + 1
            total_success += p.success_count
        
        return {
            "total_patterns": len(self._patterns),
            "by_source": by_source,
            "total_successes": total_success,
            "avg_confidence": (
                sum(p.confidence for p in self._patterns) / len(self._patterns)
                if self._patterns else 0
            )
        }
    
    def _generate_id(self, content: str) -> str:
        """Generate pattern ID"""
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _extract_name(self, pattern: str) -> str:
        """Extract a name from pattern description"""
        # Take first few words
        words = pattern.split()[:5]
        return " ".join(words)
    
    def _pattern_to_dict(self, pattern: LearnedPattern) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        return {
            "id": pattern.id,
            "name": pattern.name,
            "description": pattern.description,
            "trigger": pattern.trigger,
            "solution_template": pattern.solution_template,
            "languages": pattern.languages,
            "frameworks": pattern.frameworks,
            "tools_sequence": pattern.tools_sequence,
            "file_patterns": pattern.file_patterns,
            "success_count": pattern.success_count,
            "confidence": pattern.confidence,
            "source": pattern.source
        }
    
    def _dict_to_pattern(self, data: Dict[str, Any]) -> LearnedPattern:
        """Convert dictionary to pattern"""
        return LearnedPattern(
            id=data.get("id", self._generate_id(data.get("description", ""))),
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger=data.get("trigger", ""),
            solution_template=data.get("solution_template", ""),
            languages=data.get("languages", []),
            frameworks=data.get("frameworks", []),
            tools_sequence=data.get("tools_sequence", []),
            file_patterns=data.get("file_patterns", []),
            success_count=data.get("success_count", 0),
            confidence=data.get("confidence", 0.5),
            source=data.get("source", "imported")
        )
