"""
RyxSurf Tab Groups & Workspaces
Organize tabs into groups with colors and workspace isolation
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json

# Theme imports (with fallback)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ui.theme import COLORS, SYMBOLS, SPACING, RADIUS
except ImportError:
    COLORS = {"accent_primary": "rgba(120,140,180,1.0)", "info": "rgba(120,160,200,0.8)", "success": "rgba(120,180,140,0.8)", "warning": "rgba(200,160,100,0.8)", "bg_secondary": "rgba(25,25,28,1.0)", "border_subtle": "rgba(255,255,255,0.06)"}
    SYMBOLS = {"add": "+", "close": "×"}
    SPACING = {"xs": 4, "sm": 8, "md": 16}
    RADIUS = {"lg": 12}


@dataclass
class TabGroup:
    """A group of related tabs"""
    id: str
    name: str
    color: str
    icon: str
    tab_ids: List[int] = field(default_factory=list)
    collapsed: bool = False
    workspace_id: Optional[str] = None


@dataclass
class Workspace:
    """A workspace containing multiple tab groups"""
    id: str
    name: str
    icon: str
    color: str
    groups: List[str] = field(default_factory=list)  # Group IDs
    active: bool = False


class TabGroupManager:
    """Manage tab groups and workspaces"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path.home() / ".config" / "ryxsurf")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.groups: Dict[str, TabGroup] = {}
        self.workspaces: Dict[str, Workspace] = {}
        self.active_workspace: Optional[str] = None
        
        self._load()
        
    def _load(self):
        """Load groups and workspaces from disk"""
        groups_file = self.data_dir / "tab_groups.json"
        if groups_file.exists():
            try:
                with open(groups_file) as f:
                    data = json.load(f)
                    for group_data in data.get("groups", []):
                        group = TabGroup(**group_data)
                        self.groups[group.id] = group
            except Exception as e:
                print(f"Error loading tab groups: {e}")
                
        workspaces_file = self.data_dir / "workspaces.json"
        if workspaces_file.exists():
            try:
                with open(workspaces_file) as f:
                    data = json.load(f)
                    for ws_data in data.get("workspaces", []):
                        ws = Workspace(**ws_data)
                        self.workspaces[ws.id] = ws
                    self.active_workspace = data.get("active_workspace")
            except Exception as e:
                print(f"Error loading workspaces: {e}")
                
        # Create default workspace if none exist
        if not self.workspaces:
            self._create_default_workspaces()
            
    def _save(self):
        """Save groups and workspaces to disk"""
        groups_file = self.data_dir / "tab_groups.json"
        workspaces_file = self.data_dir / "workspaces.json"
        
        try:
            with open(groups_file, 'w') as f:
                json.dump({
                    "groups": [vars(g) for g in self.groups.values()]
                }, f, indent=2)
                
            with open(workspaces_file, 'w') as f:
                json.dump({
                    "workspaces": [vars(w) for w in self.workspaces.values()],
                    "active_workspace": self.active_workspace,
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving: {e}")
            
    def _create_default_workspaces(self):
        """Create default workspaces"""
        defaults = [
            Workspace("personal", "Personal", "⌂", COLORS["accent_primary"], []),
            Workspace("work", "Work", "⚒", COLORS["info"], []),
            Workspace("school", "School", "◆", COLORS["success"], []),
            Workspace("chill", "Chill", "♪", COLORS["warning"], []),
        ]
        for ws in defaults:
            self.workspaces[ws.id] = ws
        self.active_workspace = "personal"
        self._save()
        
    def create_group(self, name: str, color: Optional[str] = None, icon: Optional[str] = None, workspace_id: Optional[str] = None) -> TabGroup:
        """Create a new tab group"""
        import uuid
        group_id = str(uuid.uuid4())
        group = TabGroup(
            id=group_id,
            name=name,
            color=color or COLORS["accent_primary"],
            icon=icon or "●",
            workspace_id=workspace_id or self.active_workspace,
        )
        self.groups[group_id] = group
        
        # Add to workspace
        if group.workspace_id and group.workspace_id in self.workspaces:
            self.workspaces[group.workspace_id].groups.append(group_id)
            
        self._save()
        return group
        
    def delete_group(self, group_id: str):
        """Delete a tab group"""
        if group_id in self.groups:
            group = self.groups[group_id]
            
            # Remove from workspace
            if group.workspace_id and group.workspace_id in self.workspaces:
                ws = self.workspaces[group.workspace_id]
                if group_id in ws.groups:
                    ws.groups.remove(group_id)
                    
            del self.groups[group_id]
            self._save()
            
    def add_tab_to_group(self, tab_id: int, group_id: str):
        """Add a tab to a group"""
        if group_id in self.groups:
            if tab_id not in self.groups[group_id].tab_ids:
                self.groups[group_id].tab_ids.append(tab_id)
                self._save()
                
    def remove_tab_from_group(self, tab_id: int, group_id: str):
        """Remove a tab from a group"""
        if group_id in self.groups:
            if tab_id in self.groups[group_id].tab_ids:
                self.groups[group_id].tab_ids.remove(tab_id)
                self._save()
                
    def get_tab_group(self, tab_id: int) -> Optional[TabGroup]:
        """Get the group a tab belongs to"""
        for group in self.groups.values():
            if tab_id in group.tab_ids:
                return group
        return None
        
    def toggle_group_collapse(self, group_id: str):
        """Toggle group collapsed state"""
        if group_id in self.groups:
            self.groups[group_id].collapsed = not self.groups[group_id].collapsed
            self._save()
            
    def create_workspace(self, name: str, icon: str, color: str) -> Workspace:
        """Create a new workspace"""
        import uuid
        ws_id = str(uuid.uuid4())
        ws = Workspace(id=ws_id, name=name, icon=icon, color=color)
        self.workspaces[ws_id] = ws
        self._save()
        return ws
        
    def switch_workspace(self, workspace_id: str):
        """Switch to a different workspace"""
        if workspace_id in self.workspaces:
            # Deactivate old
            if self.active_workspace:
                self.workspaces[self.active_workspace].active = False
                
            # Activate new
            self.active_workspace = workspace_id
            self.workspaces[workspace_id].active = True
            self._save()
            
    def get_workspace_tabs(self, workspace_id: str) -> List[int]:
        """Get all tabs in a workspace"""
        if workspace_id not in self.workspaces:
            return []
            
        tabs = []
        ws = self.workspaces[workspace_id]
        for group_id in ws.groups:
            if group_id in self.groups:
                tabs.extend(self.groups[group_id].tab_ids)
        return tabs


class TabGroupsSidebar(Gtk.Box):
    """Sidebar showing tab groups and workspaces"""
    
    def __init__(self, manager: TabGroupManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.manager = manager
        self.set_size_request(250, -1)
        
        # Apply styling
        self.get_style_context().add_class("sidebar")
        
        self._build_ui()
        
    def _build_ui(self):
        """Build sidebar UI"""
        # Workspace switcher
        ws_box = self._create_workspace_switcher()
        self.append(ws_box)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(sep)
        
        # Groups list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        self.groups_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING['sm'])
        self.groups_list.set_margin_top(SPACING['sm'])
        self.groups_list.set_margin_bottom(SPACING['sm'])
        scroll.set_child(self.groups_list)
        
        self.append(scroll)
        
        # Add group button
        add_btn = self._create_add_group_button()
        self.append(add_btn)
        
        self._update_groups()
        
    def _create_workspace_switcher(self) -> Gtk.Box:
        """Create workspace switcher"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING['xs'])
        box.set_margin_start(SPACING['sm'])
        box.set_margin_end(SPACING['sm'])
        box.set_margin_top(SPACING['sm'])
        box.set_margin_bottom(SPACING['sm'])
        
        for ws in self.manager.workspaces.values():
            btn = Gtk.Button()
            btn.set_label(ws.icon)
            btn.set_tooltip_text(ws.name)
            
            if ws.id == self.manager.active_workspace:
                btn.get_style_context().add_class("active")
                
            btn.connect("clicked", lambda w, ws_id=ws.id: self._switch_workspace(ws_id))
            box.append(btn)
            
        return box
        
    def _switch_workspace(self, workspace_id: str):
        """Switch workspace"""
        self.manager.switch_workspace(workspace_id)
        self._build_ui()  # Rebuild
        self.emit("workspace-changed", workspace_id)
        
    def _create_add_group_button(self) -> Gtk.Button:
        """Create add group button"""
        btn = Gtk.Button()
        btn.set_label(f"{SYMBOLS['add']} New Group")
        btn.set_margin_start(SPACING['sm'])
        btn.set_margin_end(SPACING['sm'])
        btn.set_margin_bottom(SPACING['sm'])
        btn.connect("clicked", lambda w: self._show_new_group_dialog())
        return btn
        
    def _show_new_group_dialog(self):
        """Show dialog to create new group"""
        dialog = Gtk.Dialog(
            title="New Tab Group",
            transient_for=self.get_root(),
            modal=True,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        
        # Name entry
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("Group name")
        content.append(name_entry)
        
        dialog.connect("response", lambda d, r: self._on_new_group_response(d, r, name_entry.get_text()))
        dialog.present()
        
    def _on_new_group_response(self, dialog: Gtk.Dialog, response: int, name: str):
        """Handle new group dialog response"""
        if response == Gtk.ResponseType.OK and name:
            group = self.manager.create_group(name)
            self._update_groups()
            self.emit("group-created", group.id)
        dialog.close()
        
    def _update_groups(self):
        """Update groups list"""
        # Clear existing
        while True:
            child = self.groups_list.get_first_child()
            if child is None:
                break
            self.groups_list.remove(child)
            
        # Add groups for active workspace
        if self.manager.active_workspace:
            ws = self.manager.workspaces[self.manager.active_workspace]
            for group_id in ws.groups:
                if group_id in self.manager.groups:
                    group = self.manager.groups[group_id]
                    group_widget = self._create_group_widget(group)
                    self.groups_list.append(group_widget)
                    
    def _create_group_widget(self, group: TabGroup) -> Gtk.Box:
        """Create widget for a group"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING['xs'])
        box.set_margin_start(SPACING['sm'])
        box.set_margin_end(SPACING['sm'])
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING['sm'])
        
        # Collapse button
        collapse_btn = Gtk.Button()
        collapse_btn.set_label("›" if group.collapsed else "⌄")
        collapse_btn.get_style_context().add_class("flat")
        collapse_btn.connect("clicked", lambda w: self._toggle_group(group.id))
        header.append(collapse_btn)
        
        # Icon
        icon_label = Gtk.Label(label=group.icon)
        header.append(icon_label)
        
        # Name
        name_label = Gtk.Label(label=group.name)
        name_label.set_hexpand(True)
        name_label.set_halign(Gtk.Align.START)
        header.append(name_label)
        
        # Tab count
        count_label = Gtk.Label(label=str(len(group.tab_ids)))
        count_label.get_style_context().add_class("dim-label")
        header.append(count_label)
        
        box.append(header)
        
        # Tabs (if not collapsed)
        if not group.collapsed:
            for tab_id in group.tab_ids:
                tab_widget = self._create_tab_widget(tab_id, group.id)
                box.append(tab_widget)
                
        return box
        
    def _create_tab_widget(self, tab_id: int, group_id: str) -> Gtk.Button:
        """Create widget for a tab in group"""
        btn = Gtk.Button()
        btn.set_label(f"  Tab {tab_id}")
        btn.get_style_context().add_class("flat")
        btn.set_halign(Gtk.Align.START)
        btn.connect("clicked", lambda w: self.emit("tab-activated", tab_id))
        return btn
        
    def _toggle_group(self, group_id: str):
        """Toggle group collapse"""
        self.manager.toggle_group_collapse(group_id)
        self._update_groups()


# Register custom signals
from gi.repository import GObject
GObject.signal_new("workspace-changed", TabGroupsSidebar, GObject.SignalFlags.RUN_FIRST, None, (str,))
GObject.signal_new("group-created", TabGroupsSidebar, GObject.SignalFlags.RUN_FIRST, None, (str,))
GObject.signal_new("tab-activated", TabGroupsSidebar, GObject.SignalFlags.RUN_FIRST, None, (int,))
