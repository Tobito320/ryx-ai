import os
import json
from pathlib import Path
from typing import List, Dict, Optional

class SessionManager:
    """
    Manages tab sessions by saving and loading them as JSON files.
    Sessions are stored in ~/.config/ryxsurf/sessions/.
    Each session contains tabs with url, title, and scroll position.
    """

    SESSION_DIR = Path.home() / ".config" / "ryxsurf" / "sessions"

    def __init__(self):
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_name: str, tabs: List[Dict[str, str]]):
        """
        Saves the current session to a JSON file.

        :param session_name: Name of the session (e.g., 'school', 'work')
        :param tabs: List of tabs, each represented as a dictionary with 'url', 'title', and 'scroll_position'
        """
        session_file = self.SESSION_DIR / f"{session_name}.json"
        with open(session_file, 'w') as f:
            json.dump(tabs, f, indent=4)

    def load_session(self, session_name: str) -> Optional[List[Dict[str, str]]]:
        """
        Loads a session from a JSON file.

        :param session_name: Name of the session (e.g., 'school', 'work')
        :return: List of tabs if the session exists, otherwise None
        """
        session_file = self.SESSION_DIR / f"{session_name}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return None

    def list_sessions(self) -> List[str]:
        """
        Lists all available session names.

        :return: List of session names
        """
        return [file.stem for file in self.SESSION_DIR.glob("*.json")]

    def delete_session(self, session_name: str):
        """
        Deletes a session file.

        :param session_name: Name of the session to delete
        """
        session_file = self.SESSION_DIR / f"{session_name}.json"
        if session_file.exists():
            session_file.unlink()

# Example usage:
if __name__ == "__main__":
    manager = SessionManager()
    tabs = [
        {"url": "https://example.com", "title": "Example", "scroll_position": 100},
        {"url": "https://github.com", "title": "GitHub", "scroll_position": 0}
    ]
    manager.save_session("work", tabs)
    loaded_tabs = manager.load_session("work")
    print(loaded_tabs)
    print(manager.list_sessions())
    manager.delete_session("work")