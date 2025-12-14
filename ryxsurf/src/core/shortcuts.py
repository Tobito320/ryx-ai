"""
Keyboard Shortcuts Manager

Centralized keyboard shortcut management with customization.
Inspired by VS Code command palette approach.
"""

from typing import Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

log = logging.getLogger("ryxsurf.shortcuts")


@dataclass
class Shortcut:
    """Represents a keyboard shortcut"""
    id: str
    name: str
    description: str
    keys: str  # e.g., "Ctrl+T", "Alt+←"
    category: str
    action: Callable
    enabled: bool = True


class ShortcutManager:
    """Manages all keyboard shortcuts"""
    
    def __init__(self):
        self.shortcuts: Dict[str, Shortcut] = {}
        self.key_bindings: Dict[str, str] = {}  # keys -> shortcut_id
        self._init_default_shortcuts()
    
    def _init_default_shortcuts(self):
        """Initialize default shortcuts"""
        # This will be populated when actions are registered
        pass
    
    def register(self, shortcut_id: str, name: str, description: str, 
                keys: str, category: str, action: Callable):
        """Register a new shortcut"""
        shortcut = Shortcut(
            id=shortcut_id,
            name=name,
            description=description,
            keys=keys,
            category=category,
            action=action
        )
        
        self.shortcuts[shortcut_id] = shortcut
        self.key_bindings[keys] = shortcut_id
        
        log.info(f"Registered shortcut: {name} ({keys})")
    
    def unregister(self, shortcut_id: str):
        """Unregister a shortcut"""
        if shortcut_id in self.shortcuts:
            shortcut = self.shortcuts[shortcut_id]
            if shortcut.keys in self.key_bindings:
                del self.key_bindings[shortcut.keys]
            del self.shortcuts[shortcut_id]
    
    def get_shortcut_by_keys(self, keys: str) -> Optional[Shortcut]:
        """Get shortcut by key combination"""
        shortcut_id = self.key_bindings.get(keys)
        if shortcut_id:
            return self.shortcuts.get(shortcut_id)
        return None
    
    def execute(self, keys: str) -> bool:
        """Execute shortcut by keys"""
        shortcut = self.get_shortcut_by_keys(keys)
        if shortcut and shortcut.enabled:
            try:
                shortcut.action()
                return True
            except Exception as e:
                log.error(f"Failed to execute shortcut {keys}: {e}")
        return False
    
    def rebind(self, shortcut_id: str, new_keys: str):
        """Rebind a shortcut to new keys"""
        if shortcut_id in self.shortcuts:
            shortcut = self.shortcuts[shortcut_id]
            
            # Remove old binding
            if shortcut.keys in self.key_bindings:
                del self.key_bindings[shortcut.keys]
            
            # Check if new keys are already used
            if new_keys in self.key_bindings:
                existing_id = self.key_bindings[new_keys]
                log.warning(f"Keys {new_keys} already bound to {existing_id}")
                return False
            
            # Add new binding
            shortcut.keys = new_keys
            self.key_bindings[new_keys] = shortcut_id
            
            log.info(f"Rebound {shortcut_id} to {new_keys}")
            return True
        return False
    
    def enable(self, shortcut_id: str):
        """Enable a shortcut"""
        if shortcut_id in self.shortcuts:
            self.shortcuts[shortcut_id].enabled = True
    
    def disable(self, shortcut_id: str):
        """Disable a shortcut"""
        if shortcut_id in self.shortcuts:
            self.shortcuts[shortcut_id].enabled = False
    
    def get_all_by_category(self) -> Dict[str, List[Shortcut]]:
        """Get all shortcuts grouped by category"""
        categories: Dict[str, List[Shortcut]] = {}
        
        for shortcut in self.shortcuts.values():
            if shortcut.category not in categories:
                categories[shortcut.category] = []
            categories[shortcut.category].append(shortcut)
        
        return categories
    
    def search(self, query: str) -> List[Shortcut]:
        """Search shortcuts by name or description"""
        query = query.lower()
        results = []
        
        for shortcut in self.shortcuts.values():
            if (query in shortcut.name.lower() or 
                query in shortcut.description.lower() or
                query in shortcut.keys.lower()):
                results.append(shortcut)
        
        return results
    
    def serialize(self) -> dict:
        """Serialize shortcuts to dict"""
        return {
            shortcut_id: {
                "keys": shortcut.keys,
                "enabled": shortcut.enabled,
            }
            for shortcut_id, shortcut in self.shortcuts.items()
        }
    
    def deserialize(self, data: dict):
        """Deserialize shortcuts from dict"""
        for shortcut_id, shortcut_data in data.items():
            if shortcut_id in self.shortcuts:
                # Update keys if changed
                new_keys = shortcut_data.get("keys")
                if new_keys and new_keys != self.shortcuts[shortcut_id].keys:
                    self.rebind(shortcut_id, new_keys)
                
                # Update enabled state
                enabled = shortcut_data.get("enabled", True)
                if enabled:
                    self.enable(shortcut_id)
                else:
                    self.disable(shortcut_id)


# Default shortcut definitions
DEFAULT_SHORTCUTS = [
    # Navigation
    ("nav.back", "Back", "Go back in history", "Alt+←", "Navigation"),
    ("nav.forward", "Forward", "Go forward in history", "Alt+→", "Navigation"),
    ("nav.reload", "Reload", "Reload current page", "F5", "Navigation"),
    ("nav.reload_alt", "Reload", "Reload current page", "Ctrl+R", "Navigation"),
    ("nav.home", "Home", "Go to homepage", "Alt+Home", "Navigation"),
    ("nav.stop", "Stop", "Stop loading page", "Escape", "Navigation"),
    
    # Tabs
    ("tab.new", "New Tab", "Open a new tab", "Ctrl+T", "Tabs"),
    ("tab.close", "Close Tab", "Close current tab", "Ctrl+W", "Tabs"),
    ("tab.reopen", "Reopen Tab", "Reopen last closed tab", "Ctrl+Shift+T", "Tabs"),
    ("tab.next", "Next Tab", "Switch to next tab", "Ctrl+Tab", "Tabs"),
    ("tab.prev", "Previous Tab", "Switch to previous tab", "Ctrl+Shift+Tab", "Tabs"),
    ("tab.jump_1", "Jump to Tab 1", "Switch to first tab", "Ctrl+1", "Tabs"),
    ("tab.jump_2", "Jump to Tab 2", "Switch to second tab", "Ctrl+2", "Tabs"),
    ("tab.jump_3", "Jump to Tab 3", "Switch to third tab", "Ctrl+3", "Tabs"),
    ("tab.jump_4", "Jump to Tab 4", "Switch to fourth tab", "Ctrl+4", "Tabs"),
    ("tab.jump_5", "Jump to Tab 5", "Switch to fifth tab", "Ctrl+5", "Tabs"),
    ("tab.jump_6", "Jump to Tab 6", "Switch to sixth tab", "Ctrl+6", "Tabs"),
    ("tab.jump_7", "Jump to Tab 7", "Switch to seventh tab", "Ctrl+7", "Tabs"),
    ("tab.jump_8", "Jump to Tab 8", "Switch to eighth tab", "Ctrl+8", "Tabs"),
    ("tab.jump_9", "Jump to Tab 9", "Switch to last tab", "Ctrl+9", "Tabs"),
    ("tab.duplicate", "Duplicate Tab", "Duplicate current tab", "Ctrl+Shift+K", "Tabs"),
    ("tab.pin", "Pin/Unpin Tab", "Toggle tab pinning", "Ctrl+Shift+P", "Tabs"),
    
    # Window
    ("window.fullscreen", "Fullscreen", "Toggle fullscreen mode", "F11", "Window"),
    ("window.minimize", "Minimize", "Minimize window", "Ctrl+M", "Window"),
    ("window.new", "New Window", "Open new browser window", "Ctrl+N", "Window"),
    ("window.close", "Close Window", "Close current window", "Ctrl+Shift+W", "Window"),
    
    # View
    ("view.sidebar", "Toggle Sidebar", "Show/hide sidebar", "Ctrl+B", "View"),
    ("view.bookmarks_bar", "Toggle Bookmarks Bar", "Show/hide bookmarks bar", "Ctrl+Shift+B", "View"),
    ("view.url_bar", "Focus URL Bar", "Focus address bar", "Ctrl+L", "View"),
    ("view.url_bar_alt", "Focus URL Bar", "Focus address bar", "F6", "View"),
    ("view.zoom_in", "Zoom In", "Increase page zoom", "Ctrl++", "View"),
    ("view.zoom_out", "Zoom Out", "Decrease page zoom", "Ctrl+-", "View"),
    ("view.zoom_reset", "Reset Zoom", "Reset page zoom", "Ctrl+0", "View"),
    ("view.reader_mode", "Reader Mode", "Toggle reader mode", "F9", "View"),
    
    # Search & Find
    ("search.find", "Find in Page", "Open find bar", "Ctrl+F", "Search"),
    ("search.find_next", "Find Next", "Find next match", "F3", "Search"),
    ("search.find_prev", "Find Previous", "Find previous match", "Shift+F3", "Search"),
    
    # Page
    ("page.save", "Save Page", "Save current page", "Ctrl+S", "Page"),
    ("page.print", "Print", "Print current page", "Ctrl+P", "Page"),
    ("page.screenshot", "Screenshot", "Take page screenshot", "Ctrl+Shift+S", "Page"),
    ("page.view_source", "View Source", "View page source", "Ctrl+U", "Page"),
    
    # Bookmarks
    ("bookmark.add", "Bookmark Page", "Add current page to bookmarks", "Ctrl+D", "Bookmarks"),
    ("bookmark.manager", "Bookmark Manager", "Open bookmark manager", "Ctrl+Shift+O", "Bookmarks"),
    
    # History
    ("history.show", "Show History", "Open history panel", "Ctrl+H", "History"),
    ("history.clear", "Clear History", "Clear browsing history", "Ctrl+Shift+Delete", "History"),
    
    # Downloads
    ("downloads.show", "Show Downloads", "Open downloads panel", "Ctrl+J", "Downloads"),
    
    # Developer
    ("dev.inspector", "Inspector", "Open element inspector", "F12", "Developer"),
    ("dev.inspector_alt", "Inspector", "Open element inspector", "Ctrl+Shift+I", "Developer"),
    ("dev.console", "Console", "Open developer console", "Ctrl+Shift+J", "Developer"),
    
    # Settings
    ("settings.show", "Settings", "Open settings", "Ctrl+,", "Settings"),
    ("settings.shortcuts", "Keyboard Shortcuts", "Open shortcuts editor", "Ctrl+K Ctrl+S", "Settings"),
    
    # Split View
    ("split.vertical", "Split Vertical", "Split view vertically", "Ctrl+\\", "Split View"),
    ("split.horizontal", "Split Horizontal", "Split view horizontally", "Ctrl+Shift+\\", "Split View"),
    ("split.close", "Close Split", "Exit split view", "Ctrl+Shift+X", "Split View"),
    
    # Workspaces
    ("workspace.next", "Next Workspace", "Switch to next workspace", "Ctrl+Shift+]", "Workspaces"),
    ("workspace.prev", "Previous Workspace", "Switch to previous workspace", "Ctrl+Shift+[", "Workspaces"),
    
    # Quick Actions
    ("quick.command_palette", "Command Palette", "Open command palette", "Ctrl+Shift+P", "Quick Actions"),
    ("quick.tab_search", "Tab Search", "Search open tabs", "Ctrl+Shift+A", "Quick Actions"),
]


def get_key_display_name(keys: str) -> str:
    """Convert key string to display format"""
    # Handle special keys
    replacements = {
        "Ctrl": "⌃",
        "Alt": "⌥",
        "Shift": "⇧",
        "Super": "◆",
        "←": "←",
        "→": "→",
        "↑": "↑",
        "↓": "↓",
    }
    
    result = keys
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result
