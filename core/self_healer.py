"""
Ryx AI - Self Healing System

AI-driven cache cleanup and knowledge maintenance.
Uses a powerful model to analyze cached data and remove useless entries
that might make smaller models dumber.

NO hardcoded rules - the AI decides what's useful and what's not.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CleanupResult:
    """Result of a self-healing operation"""
    entries_reviewed: int = 0
    entries_removed: int = 0
    entries_improved: int = 0
    space_freed_kb: float = 0.0
    summary: str = ""
    details: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []


class SelfHealer:
    """
    AI-driven self-healing for Ryx's knowledge and cache.
    
    Uses a smart model to:
    - Review cached interactions
    - Identify useless/low-quality entries (greetings, small talk, errors)
    - Remove entries that degrade smaller model performance
    - Consolidate/improve valuable knowledge
    """
    
    # Prompt for the healing AI - it decides what's useful
    HEALING_PROMPT = '''You are a knowledge curator for an AI assistant called Ryx.
Your job is to review cached interactions and decide what to KEEP vs REMOVE.

REMOVE entries that:
- Are simple greetings (hello, hi, hey, etc.)
- Are small talk with no useful information
- Are test queries or debugging noise
- Are errors or failed attempts
- Are duplicate/redundant with other entries
- Would make a smaller model give worse answers if it learns from them

KEEP entries that:
- Contain user preferences (editor choice, file paths, coding style)
- Show successful task completions
- Have useful technical information
- Demonstrate good problem-solving patterns

Review these entries and return a JSON object:
{{
    "remove_ids": [list of entry IDs to remove],
    "keep_ids": [list of entry IDs to keep],
    "reasoning": "brief explanation of cleanup decisions"
}}

Entries to review:
{entries}
'''

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize self-healer"""
        if data_dir is None:
            from core.paths import get_data_dir
            data_dir = get_data_dir()
        
        self.data_dir = Path(data_dir)
        self.ollama = None
    
    def _get_ollama(self):
        """Get Ollama client lazily"""
        if self.ollama is None:
            from core.ollama_client import OllamaClient
            self.ollama = OllamaClient()
        return self.ollama
    
    def heal(self, aggressive: bool = False) -> CleanupResult:
        """
        Run self-healing on all knowledge stores.
        
        Args:
            aggressive: If True, be more aggressive about removing entries
            
        Returns:
            CleanupResult with summary of actions taken
        """
        result = CleanupResult()
        
        # Heal each database
        result.details.append("🔍 Analyzing knowledge stores...")
        
        # 1. Meta learning interactions
        ml_result = self._heal_meta_learning(aggressive)
        result.entries_reviewed += ml_result.entries_reviewed
        result.entries_removed += ml_result.entries_removed
        result.details.extend(ml_result.details)
        
        # 2. Experience cache
        exp_result = self._heal_experience_cache(aggressive)
        result.entries_reviewed += exp_result.entries_reviewed
        result.entries_removed += exp_result.entries_removed
        result.details.extend(exp_result.details)
        
        # 3. RAG knowledge
        rag_result = self._heal_rag_knowledge(aggressive)
        result.entries_reviewed += rag_result.entries_reviewed
        result.entries_removed += rag_result.entries_removed
        result.details.extend(rag_result.details)
        
        # Generate summary
        if result.entries_removed > 0:
            result.summary = f"✅ Cleaned {result.entries_removed} low-quality entries from {result.entries_reviewed} reviewed"
        else:
            result.summary = f"✅ Knowledge is healthy - reviewed {result.entries_reviewed} entries, nothing to remove"
        
        return result
    
    def _heal_meta_learning(self, aggressive: bool) -> CleanupResult:
        """Heal meta_learning.db interactions"""
        result = CleanupResult()
        db_path = self.data_dir / "meta_learning.db"
        
        if not db_path.exists():
            result.details.append("  └─ meta_learning.db: not found (skip)")
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get recent interactions
            cursor.execute("""
                SELECT id, query, response, model_used 
                FROM interactions 
                ORDER BY id DESC 
                LIMIT 100
            """)
            rows = cursor.fetchall()
            
            if not rows:
                result.details.append("  └─ meta_learning.db: empty (skip)")
                conn.close()
                return result
            
            result.entries_reviewed = len(rows)
            
            # Format entries for AI review
            entries = []
            for row in rows:
                entries.append({
                    "id": row[0],
                    "query": row[1][:200] if row[1] else "",
                    "response": row[2][:200] if row[2] else "",
                    "model": row[3]
                })
            
            # Ask AI what to remove
            remove_ids = self._ask_ai_for_cleanup(entries, aggressive)
            
            if remove_ids:
                placeholders = ",".join("?" * len(remove_ids))
                cursor.execute(f"DELETE FROM interactions WHERE id IN ({placeholders})", remove_ids)
                conn.commit()
                result.entries_removed = len(remove_ids)
            
            conn.close()
            result.details.append(f"  └─ meta_learning.db: reviewed {result.entries_reviewed}, removed {result.entries_removed}")
            
        except Exception as e:
            result.details.append(f"  └─ meta_learning.db: error - {e}")
        
        return result
    
    def _heal_experience_cache(self, aggressive: bool) -> CleanupResult:
        """Heal experience_cache.db"""
        result = CleanupResult()
        db_path = self.data_dir / "experience_cache.db"
        
        if not db_path.exists():
            result.details.append("  └─ experience_cache.db: not found (skip)")
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, instruction, intent_type, success 
                FROM experiences 
                ORDER BY id DESC 
                LIMIT 100
            """)
            rows = cursor.fetchall()
            
            if not rows:
                result.details.append("  └─ experience_cache.db: empty (skip)")
                conn.close()
                return result
            
            result.entries_reviewed = len(rows)
            
            entries = []
            for row in rows:
                entries.append({
                    "id": row[0],
                    "instruction": row[1][:200] if row[1] else "",
                    "intent": row[2],
                    "success": row[3]
                })
            
            remove_ids = self._ask_ai_for_cleanup(entries, aggressive)
            
            if remove_ids:
                placeholders = ",".join("?" * len(remove_ids))
                cursor.execute(f"DELETE FROM experiences WHERE id IN ({placeholders})", remove_ids)
                conn.commit()
                result.entries_removed = len(remove_ids)
            
            conn.close()
            result.details.append(f"  └─ experience_cache.db: reviewed {result.entries_reviewed}, removed {result.entries_removed}")
            
        except Exception as e:
            result.details.append(f"  └─ experience_cache.db: error - {e}")
        
        return result
    
    def _heal_rag_knowledge(self, aggressive: bool) -> CleanupResult:
        """Heal rag_knowledge.db"""
        result = CleanupResult()
        db_path = self.data_dir / "rag_knowledge.db"
        
        if not db_path.exists():
            result.details.append("  └─ rag_knowledge.db: not found (skip)")
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check what tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                result.details.append("  └─ rag_knowledge.db: no tables (skip)")
                conn.close()
                return result
            
            result.details.append(f"  └─ rag_knowledge.db: {len(tables)} tables (preserved)")
            conn.close()
            
        except Exception as e:
            result.details.append(f"  └─ rag_knowledge.db: error - {e}")
        
        return result
    
    def _ask_ai_for_cleanup(self, entries: List[Dict], aggressive: bool) -> List[int]:
        """Ask AI which entries to remove"""
        if not entries:
            return []
        
        ollama = self._get_ollama()
        
        # Use a capable model for cleanup decisions
        prompt = self.HEALING_PROMPT.format(entries=json.dumps(entries, indent=2))
        
        if aggressive:
            prompt += "\n\nBe AGGRESSIVE - remove anything that isn't clearly valuable."
        
        response = ollama.generate(
            prompt=prompt,
            model="qwen2.5-coder:14b",  # Use capable model for cleanup decisions
            system="You are a data curator. Return ONLY valid JSON, no explanation.",
            max_tokens=500
        )
        
        if response.error:
            return []
        
        # Parse response
        try:
            clean = response.response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
            
            data = json.loads(clean)
            return data.get("remove_ids", [])
        except:
            return []


def run_self_healing(aggressive: bool = False) -> CleanupResult:
    """
    Convenience function to run self-healing.
    
    Args:
        aggressive: Be more aggressive about removing entries
        
    Returns:
        CleanupResult with summary
    """
    healer = SelfHealer()
    return healer.heal(aggressive)
