"""
RyxSurf Session Manager

Handles saving, loading, and switching between tab sessions.
Sessions are named groups of tabs (school, work, chill, etc.)
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TabState:
    """Serializable tab state"""
    url: str
    title: str
    scroll_position: int = 0
    is_pinned: bool = False
    favicon_url: Optional[str] = None


@dataclass 
class SessionState:
    """A complete session with all tabs"""
    name: str
    tabs: List[TabState] = field(default_factory=list)
    active_tab: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    color: str = "#6272a4"  # Dracula purple default
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tabs": [asdict(t) for t in self.tabs],
            "active_tab": self.active_tab,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionState':
        tabs = [TabState(**t) for t in data.get("tabs", [])]
        return cls(
            name=data["name"],
            tabs=tabs,
            active_tab=data.get("active_tab", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            color=data.get("color", "#6272a4")
        )


class SessionManager:
    """
    Manages browser sessions.
    
    Features:
    - Save/load sessions to disk
    - Quick switch between sessions
    - Auto-save on tab changes
    - Session colors for visual distinction
    """
    
    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = session_dir or Path.home() / ".config" / "ryxsurf" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: str = "default"
        self.sessions: Dict[str, SessionState] = {}
        
        # Load existing sessions
        self._load_all_sessions()
        
    def _load_all_sessions(self):
        """Load all sessions from disk"""
        for session_file in self.session_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                session = SessionState.from_dict(data)
                self.sessions[session.name] = session
            except Exception as e:
                print(f"Failed to load session {session_file}: {e}")
                
        # Ensure default session exists
        if "default" not in self.sessions:
            self.sessions["default"] = SessionState(name="default")
            
    def save_session(self, name: str, tabs: List[TabState], active_tab: int = 0):
        """Save a session to disk"""
        if name in self.sessions:
            session = self.sessions[name]
            session.tabs = tabs
            session.active_tab = active_tab
            session.updated_at = datetime.now().isoformat()
        else:
            session = SessionState(
                name=name,
                tabs=tabs,
                active_tab=active_tab
            )
            self.sessions[name] = session
            
        # Write to disk
        session_file = self.session_dir / f"{name}.json"
        session_file.write_text(json.dumps(session.to_dict(), indent=2))
        
    def load_session(self, name: str) -> Optional[SessionState]:
        """Load a session by name"""
        return self.sessions.get(name)
        
    def switch_session(self, name: str) -> Optional[SessionState]:
        """Switch to a different session"""
        if name not in self.sessions:
            return None
            
        self.current_session = name
        return self.sessions[name]
        
    def list_sessions(self) -> List[str]:
        """List all session names"""
        return list(self.sessions.keys())
        
    def delete_session(self, name: str) -> bool:
        """Delete a session"""
        if name == "default":
            return False  # Can't delete default
            
        if name in self.sessions:
            del self.sessions[name]
            session_file = self.session_dir / f"{name}.json"
            if session_file.exists():
                session_file.unlink()
            return True
        return False
        
    def rename_session(self, old_name: str, new_name: str) -> bool:
        """Rename a session"""
        if old_name not in self.sessions or new_name in self.sessions:
            return False
            
        session = self.sessions.pop(old_name)
        session.name = new_name
        self.sessions[new_name] = session
        
        # Rename file
        old_file = self.session_dir / f"{old_name}.json"
        new_file = self.session_dir / f"{new_name}.json"
        
        if old_file.exists():
            old_file.rename(new_file)
            
        return True
        
    def set_session_color(self, name: str, color: str):
        """Set session color for UI"""
        if name in self.sessions:
            self.sessions[name].color = color
            self.save_session(name, self.sessions[name].tabs, self.sessions[name].active_tab)
            
    def get_session_info(self) -> List[Dict]:
        """Get info about all sessions for UI"""
        return [
            {
                "name": s.name,
                "tab_count": len(s.tabs),
                "color": s.color,
                "updated_at": s.updated_at,
                "is_current": s.name == self.current_session
            }
            for s in self.sessions.values()
        ]
        
    def quick_switch(self, session_name: str) -> Optional[SessionState]:
        """Quickly switch to a different session by saving the current one and loading the new one."""
        self.save_session(self.current_session, self.sessions[self.current_session].tabs, self.sessions[self.current_session].active_tab)
        return self.switch_session(session_name)