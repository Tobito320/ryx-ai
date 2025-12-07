"""
Memory System for RyxHub - Like ChatGPT Memory
Stores facts about the user, learns from conversations
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


DATA_DIR = Path(__file__).parent.parent / "data"
MEMORY_FILE = DATA_DIR / "user_memory.json"
USER_PROFILE_FILE = DATA_DIR / "user_profile.json"


class MemoryEntry(BaseModel):
    id: str
    type: str  # fact, preference, contact, routine, appointment
    key: str
    value: str
    confidence: float = 1.0
    source: Optional[str] = None
    created_at: str
    updated_at: str
    usage_count: int = 0


class UserProfile(BaseModel):
    """Core user information - always available to AI"""
    name: str = ""
    full_name: str = ""
    address: str = ""
    city: str = ""
    postal_code: str = ""
    email_default: str = ""
    phone: str = ""
    birth_date: str = ""
    occupation: str = ""
    employer: str = ""
    preferences: Dict[str, Any] = {}


class MemorySystem:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.memories: List[MemoryEntry] = []
        self.profile = UserProfile()
        self.load()
    
    def load(self):
        """Load memories and profile from disk"""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                    self.memories = [MemoryEntry(**m) for m in data]
            except Exception:
                self.memories = []
        
        if USER_PROFILE_FILE.exists():
            try:
                with open(USER_PROFILE_FILE, "r") as f:
                    data = json.load(f)
                    self.profile = UserProfile(**data)
            except Exception:
                self.profile = UserProfile()
    
    def save(self):
        """Save memories and profile to disk"""
        with open(MEMORY_FILE, "w") as f:
            json.dump([m.model_dump() for m in self.memories], f, indent=2)
        
        with open(USER_PROFILE_FILE, "w") as f:
            json.dump(self.profile.model_dump(), f, indent=2)
    
    def add_memory(self, type: str, key: str, value: str, source: str = None) -> MemoryEntry:
        """Add a new memory"""
        # Check if memory with same key exists
        existing = next((m for m in self.memories if m.key == key), None)
        
        now = datetime.now().isoformat()
        
        if existing:
            existing.value = value
            existing.updated_at = now
            existing.usage_count += 1
            if source:
                existing.source = source
            self.save()
            return existing
        
        memory = MemoryEntry(
            id=f"mem_{len(self.memories)}_{datetime.now().timestamp()}",
            type=type,
            key=key,
            value=value,
            source=source,
            created_at=now,
            updated_at=now,
        )
        self.memories.append(memory)
        self.save()
        return memory
    
    def get_memories(self, type: str = None, limit: int = 50) -> List[MemoryEntry]:
        """Get memories, optionally filtered by type"""
        memories = self.memories
        if type:
            memories = [m for m in memories if m.type == type]
        return sorted(memories, key=lambda m: m.updated_at, reverse=True)[:limit]
    
    def search_memories(self, query: str) -> List[MemoryEntry]:
        """Search memories by key or value"""
        query_lower = query.lower()
        return [
            m for m in self.memories
            if query_lower in m.key.lower() or query_lower in m.value.lower()
        ]
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        for i, m in enumerate(self.memories):
            if m.id == memory_id:
                self.memories.pop(i)
                self.save()
                return True
        return False
    
    def update_profile(self, **kwargs) -> UserProfile:
        """Update user profile fields"""
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
        self.save()
        return self.profile
    
    def get_context_for_ai(self) -> str:
        """Generate context string for AI prompts"""
        context_parts = []
        
        # Profile info
        if self.profile.name:
            context_parts.append(f"User's name: {self.profile.name}")
        if self.profile.full_name:
            context_parts.append(f"Full name: {self.profile.full_name}")
        if self.profile.address:
            context_parts.append(f"Address: {self.profile.address}, {self.profile.postal_code} {self.profile.city}")
        if self.profile.email_default:
            context_parts.append(f"Email: {self.profile.email_default}")
        if self.profile.occupation:
            context_parts.append(f"Occupation: {self.profile.occupation}")
        if self.profile.employer:
            context_parts.append(f"Employer: {self.profile.employer}")
        
        # Recent memories
        recent = self.get_memories(limit=20)
        if recent:
            context_parts.append("\nUser facts:")
            for m in recent:
                context_parts.append(f"- {m.key}: {m.value}")
        
        return "\n".join(context_parts)
    
    def extract_facts_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract potential facts from user text (called by AI)"""
        # This would be enhanced by the LLM to extract facts
        facts = []
        
        # Simple pattern matching for common facts
        import re
        
        # Email patterns
        emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        for email in emails:
            facts.append({"type": "contact", "key": "email", "value": email})
        
        # Phone patterns (German)
        phones = re.findall(r'\b(?:\+49|0)[\d\s/-]{8,15}\b', text)
        for phone in phones:
            facts.append({"type": "contact", "key": "phone", "value": phone})
        
        # Address patterns
        if "straße" in text.lower() or "strasse" in text.lower():
            # Could be an address
            pass
        
        return facts


# Singleton instance
memory_system = MemorySystem()
