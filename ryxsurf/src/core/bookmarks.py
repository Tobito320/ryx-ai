"""
RyxSurf Bookmark Manager

Handles bookmark storage and retrieval with:
- Quick bookmark with Ctrl+D
- Bookmark bar toggle with Ctrl+Shift+B
- JSON storage in ~/.config/ryxsurf/bookmarks.json
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse


BOOKMARKS_FILE = Path.home() / ".config" / "ryxsurf" / "bookmarks.json"


@dataclass
class Bookmark:
    """A single bookmark entry"""
    url: str
    title: str
    favicon: Optional[str] = None
    folder: str = ""  # Empty string = bookmark bar
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bookmark':
        return cls(**data)
    
    @property
    def domain(self) -> str:
        """Get domain from URL"""
        try:
            parsed = urlparse(self.url)
            return parsed.netloc
        except:
            return ""


class BookmarkManager:
    """
    Manages bookmarks with persistence.
    
    Features:
    - Add/remove bookmarks
    - Folder organization
    - Quick bookmark (Ctrl+D)
    - Bookmark bar items
    """
    
    def __init__(self):
        self.bookmarks: List[Bookmark] = []
        self._load()
        
    def _load(self):
        """Load bookmarks from file"""
        if BOOKMARKS_FILE.exists():
            try:
                data = json.loads(BOOKMARKS_FILE.read_text())
                self.bookmarks = [Bookmark.from_dict(b) for b in data.get("bookmarks", [])]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Failed to load bookmarks: {e}")
                self.bookmarks = []
        else:
            self.bookmarks = []
            
    def _save(self):
        """Save bookmarks to file"""
        BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "bookmarks": [b.to_dict() for b in self.bookmarks]
        }
        BOOKMARKS_FILE.write_text(json.dumps(data, indent=2))
        
    def add(self, url: str, title: str, folder: str = "", favicon: Optional[str] = None) -> Bookmark:
        """Add a new bookmark"""
        # Check if already bookmarked
        existing = self.get_by_url(url)
        if existing:
            return existing
            
        bookmark = Bookmark(url=url, title=title, folder=folder, favicon=favicon)
        self.bookmarks.append(bookmark)
        self._save()
        return bookmark
        
    def remove(self, url: str) -> bool:
        """Remove a bookmark by URL"""
        for i, b in enumerate(self.bookmarks):
            if b.url == url:
                self.bookmarks.pop(i)
                self._save()
                return True
        return False
        
    def toggle(self, url: str, title: str, folder: str = "", favicon: Optional[str] = None) -> tuple[bool, Optional[Bookmark]]:
        """Toggle bookmark - add if not exists, remove if exists. Returns (is_bookmarked, bookmark)"""
        existing = self.get_by_url(url)
        if existing:
            self.remove(url)
            return (False, None)
        else:
            bookmark = self.add(url, title, folder, favicon)
            return (True, bookmark)
            
    def get_by_url(self, url: str) -> Optional[Bookmark]:
        """Get bookmark by URL"""
        for b in self.bookmarks:
            if b.url == url:
                return b
        return None
        
    def is_bookmarked(self, url: str) -> bool:
        """Check if URL is bookmarked"""
        return self.get_by_url(url) is not None
        
    def get_bar_bookmarks(self) -> List[Bookmark]:
        """Get bookmarks for the bookmark bar (no folder)"""
        return [b for b in self.bookmarks if not b.folder]
        
    def get_folder_bookmarks(self, folder: str) -> List[Bookmark]:
        """Get bookmarks in a specific folder"""
        return [b for b in self.bookmarks if b.folder == folder]
        
    def get_folders(self) -> List[str]:
        """Get list of all folders"""
        folders = set()
        for b in self.bookmarks:
            if b.folder:
                folders.add(b.folder)
        return sorted(folders)
        
    def search(self, query: str) -> List[Bookmark]:
        """Search bookmarks by title or URL"""
        query = query.lower()
        return [
            b for b in self.bookmarks
            if query in b.title.lower() or query in b.url.lower()
        ]
