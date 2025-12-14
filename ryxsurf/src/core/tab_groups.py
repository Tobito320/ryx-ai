"""
Tab Groups - Chrome Feature

Organize tabs into colored groups with labels.
Supports collapsing/expanding groups.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field
import logging

log = logging.getLogger("ryxsurf.tab_groups")


@dataclass
class TabGroup:
    """Represents a group of tabs"""
    id: str
    name: str
    color: str  # Hex color
    collapsed: bool = False
    tab_ids: List[int] = field(default_factory=list)


class TabGroupManager:
    """Manages tab groups"""
    
    # Subtle color palette (not too bright)
    COLORS = {
        "gray": "#6b7280",
        "blue": "#3b82f6",
        "green": "#22c55e",
        "yellow": "#eab308",
        "orange": "#f97316",
        "red": "#ef4444",
        "purple": "#a855f7",
        "pink": "#ec4899",
        "cyan": "#06b6d4",
        "lime": "#84cc16",
    }
    
    def __init__(self):
        self.groups: Dict[str, TabGroup] = {}
        self._next_group_id = 1
    
    def create_group(self, name: str, color: str, tab_ids: List[int] = None) -> TabGroup:
        """Create a new tab group"""
        group_id = f"group_{self._next_group_id}"
        self._next_group_id += 1
        
        # Validate color
        if color not in self.COLORS:
            color = "gray"
        
        group = TabGroup(
            id=group_id,
            name=name,
            color=self.COLORS[color],
            tab_ids=tab_ids or []
        )
        
        self.groups[group_id] = group
        log.info(f"Created tab group: {name} ({len(tab_ids or [])} tabs)")
        return group
    
    def delete_group(self, group_id: str):
        """Delete a tab group"""
        if group_id in self.groups:
            group = self.groups[group_id]
            del self.groups[group_id]
            log.info(f"Deleted tab group: {group.name}")
            return group.tab_ids
        return []
    
    def add_tab_to_group(self, group_id: str, tab_id: int):
        """Add a tab to a group"""
        if group_id in self.groups:
            if tab_id not in self.groups[group_id].tab_ids:
                self.groups[group_id].tab_ids.append(tab_id)
                log.info(f"Added tab {tab_id} to group {group_id}")
    
    def remove_tab_from_group(self, group_id: str, tab_id: int):
        """Remove a tab from a group"""
        if group_id in self.groups:
            if tab_id in self.groups[group_id].tab_ids:
                self.groups[group_id].tab_ids.remove(tab_id)
                log.info(f"Removed tab {tab_id} from group {group_id}")
    
    def get_group_for_tab(self, tab_id: int) -> Optional[TabGroup]:
        """Get the group a tab belongs to"""
        for group in self.groups.values():
            if tab_id in group.tab_ids:
                return group
        return None
    
    def toggle_collapse(self, group_id: str):
        """Toggle group collapsed state"""
        if group_id in self.groups:
            self.groups[group_id].collapsed = not self.groups[group_id].collapsed
            log.info(f"Group {group_id} {'collapsed' if self.groups[group_id].collapsed else 'expanded'}")
    
    def rename_group(self, group_id: str, new_name: str):
        """Rename a group"""
        if group_id in self.groups:
            old_name = self.groups[group_id].name
            self.groups[group_id].name = new_name
            log.info(f"Renamed group from '{old_name}' to '{new_name}'")
    
    def change_group_color(self, group_id: str, color: str):
        """Change group color"""
        if group_id in self.groups and color in self.COLORS:
            self.groups[group_id].color = self.COLORS[color]
            log.info(f"Changed group {group_id} color to {color}")
    
    def get_all_groups(self) -> List[TabGroup]:
        """Get all tab groups"""
        return list(self.groups.values())
    
    def get_group_by_id(self, group_id: str) -> Optional[TabGroup]:
        """Get a specific group"""
        return self.groups.get(group_id)
    
    def auto_group_by_domain(self, tabs: List[tuple]) -> Dict[str, List[int]]:
        """
        Automatically group tabs by domain
        
        Args:
            tabs: List of (tab_id, url) tuples
            
        Returns:
            Dict of domain -> [tab_ids]
        """
        from urllib.parse import urlparse
        
        domain_groups = {}
        
        for tab_id, url in tabs:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')
                
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(tab_id)
            except Exception as e:
                log.error(f"Failed to parse URL {url}: {e}")
        
        # Only create groups for domains with 2+ tabs
        grouped_domains = {d: tabs for d, tabs in domain_groups.items() if len(tabs) >= 2}
        
        log.info(f"Auto-grouped {len(grouped_domains)} domains")
        return grouped_domains
    
    def create_groups_from_domains(self, domain_groups: Dict[str, List[int]]):
        """Create tab groups from domain grouping"""
        color_cycle = list(self.COLORS.keys())
        color_idx = 0
        
        for domain, tab_ids in domain_groups.items():
            # Clean up domain name for display
            name = domain.replace('.com', '').replace('.org', '').replace('.net', '')
            name = name.capitalize()
            
            color = color_cycle[color_idx % len(color_cycle)]
            color_idx += 1
            
            self.create_group(name, color, tab_ids)
    
    def serialize(self) -> dict:
        """Serialize groups to dict"""
        return {
            group_id: {
                "name": group.name,
                "color": group.color,
                "collapsed": group.collapsed,
                "tab_ids": group.tab_ids,
            }
            for group_id, group in self.groups.items()
        }
    
    def deserialize(self, data: dict):
        """Deserialize groups from dict"""
        self.groups.clear()
        
        for group_id, group_data in data.items():
            group = TabGroup(
                id=group_id,
                name=group_data["name"],
                color=group_data["color"],
                collapsed=group_data.get("collapsed", False),
                tab_ids=group_data.get("tab_ids", []),
            )
            self.groups[group_id] = group
        
        # Update next ID
        if self.groups:
            max_id = max(int(gid.split('_')[1]) for gid in self.groups.keys())
            self._next_group_id = max_id + 1


class TabGroupUI:
    """Helper for rendering tab groups in UI"""
    
    @staticmethod
    def get_group_badge_css(color: str) -> str:
        """Get CSS class for group badge"""
        return f"""
        .tab-group-badge {{
            background: {color};
            width: 3px;
            height: 100%;
            position: absolute;
            left: 0;
            top: 0;
        }}
        """
    
    @staticmethod
    def should_show_tab(tab_id: int, group: Optional[TabGroup]) -> bool:
        """Check if tab should be visible (not in collapsed group)"""
        if group is None:
            return True
        return not group.collapsed
