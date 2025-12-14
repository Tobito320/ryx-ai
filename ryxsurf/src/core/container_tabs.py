"""
Container Tabs - Firefox Feature

Isolate cookies and storage per container for multi-account support.
Each container has its own identity with color and icon.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import logging

log = logging.getLogger("ryxsurf.containers")


@dataclass
class Container:
    """Represents a container identity"""
    id: str
    name: str
    color: str
    icon: str
    
    def __hash__(self):
        return hash(self.id)


class ContainerManager:
    """Manages container tabs"""
    
    # Subtle colors for containers
    COLORS = {
        "blue": "#3b82f6",
        "green": "#22c55e",
        "orange": "#f97316",
        "red": "#ef4444",
        "purple": "#a855f7",
        "pink": "#ec4899",
        "yellow": "#eab308",
        "cyan": "#06b6d4",
        "gray": "#6b7280",
    }
    
    # Simple geometric symbols instead of emojis
    ICONS = {
        "circle": "○",
        "square": "□",
        "triangle": "△",
        "diamond": "◇",
        "star": "☆",
        "plus": "+",
        "cross": "×",
        "dot": "·",
    }
    
    # Default containers
    DEFAULT_CONTAINERS = [
        {"id": "personal", "name": "Personal", "color": "blue", "icon": "circle"},
        {"id": "work", "name": "Work", "color": "orange", "icon": "square"},
        {"id": "shopping", "name": "Shopping", "color": "green", "icon": "triangle"},
        {"id": "banking", "name": "Banking", "color": "red", "icon": "diamond"},
    ]
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.containers: Dict[str, Container] = {}
        self._next_id = 1
        
        # Initialize default containers
        self._init_default_containers()
    
    def _init_default_containers(self):
        """Initialize default containers"""
        for data in self.DEFAULT_CONTAINERS:
            container = Container(
                id=data["id"],
                name=data["name"],
                color=self.COLORS[data["color"]],
                icon=self.ICONS[data["icon"]]
            )
            self.containers[container.id] = container
    
    def create_container(self, name: str, color: str, icon: str) -> Container:
        """Create a new container"""
        container_id = f"container_{self._next_id}"
        self._next_id += 1
        
        # Validate color and icon
        if color not in self.COLORS:
            color = "blue"
        if icon not in self.ICONS:
            icon = "circle"
        
        container = Container(
            id=container_id,
            name=name,
            color=self.COLORS[color],
            icon=self.ICONS[icon]
        )
        
        self.containers[container_id] = container
        self._create_container_storage(container_id)
        
        log.info(f"Created container: {name}")
        return container
    
    def delete_container(self, container_id: str):
        """Delete a container"""
        if container_id in self.containers:
            container = self.containers[container_id]
            del self.containers[container_id]
            self._delete_container_storage(container_id)
            log.info(f"Deleted container: {container.name}")
    
    def get_container(self, container_id: str) -> Optional[Container]:
        """Get a container by ID"""
        return self.containers.get(container_id)
    
    def get_all_containers(self) -> List[Container]:
        """Get all containers"""
        return list(self.containers.values())
    
    def rename_container(self, container_id: str, new_name: str):
        """Rename a container"""
        if container_id in self.containers:
            old_name = self.containers[container_id].name
            self.containers[container_id].name = new_name
            log.info(f"Renamed container from '{old_name}' to '{new_name}'")
    
    def change_container_color(self, container_id: str, color: str):
        """Change container color"""
        if container_id in self.containers and color in self.COLORS:
            self.containers[container_id].color = self.COLORS[color]
            log.info(f"Changed container {container_id} color to {color}")
    
    def change_container_icon(self, container_id: str, icon: str):
        """Change container icon"""
        if container_id in self.containers and icon in self.ICONS:
            self.containers[container_id].icon = self.ICONS[icon]
            log.info(f"Changed container {container_id} icon to {icon}")
    
    def _create_container_storage(self, container_id: str):
        """Create isolated storage directory for container"""
        container_dir = self.data_dir / "containers" / container_id
        container_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (container_dir / "cookies").mkdir(exist_ok=True)
        (container_dir / "localstorage").mkdir(exist_ok=True)
        (container_dir / "cache").mkdir(exist_ok=True)
        
        log.info(f"Created storage for container {container_id}")
    
    def _delete_container_storage(self, container_id: str):
        """Delete container storage"""
        import shutil
        
        container_dir = self.data_dir / "containers" / container_id
        if container_dir.exists():
            shutil.rmtree(container_dir)
            log.info(f"Deleted storage for container {container_id}")
    
    def get_container_data_dir(self, container_id: str) -> Path:
        """Get data directory for a container"""
        return self.data_dir / "containers" / container_id
    
    def serialize(self) -> dict:
        """Serialize containers to dict"""
        return {
            container_id: {
                "name": container.name,
                "color": container.color,
                "icon": container.icon,
            }
            for container_id, container in self.containers.items()
        }
    
    def deserialize(self, data: dict):
        """Deserialize containers from dict"""
        self.containers.clear()
        
        for container_id, container_data in data.items():
            container = Container(
                id=container_id,
                name=container_data["name"],
                color=container_data["color"],
                icon=container_data["icon"],
            )
            self.containers[container_id] = container
        
        # Update next ID
        custom_ids = [cid for cid in self.containers.keys() if cid.startswith("container_")]
        if custom_ids:
            max_id = max(int(cid.split('_')[1]) for cid in custom_ids)
            self._next_id = max_id + 1


class ContainerTab:
    """Associates a tab with a container"""
    
    def __init__(self, tab_id: int, container_id: str):
        self.tab_id = tab_id
        self.container_id = container_id
    
    def __repr__(self):
        return f"ContainerTab(tab={self.tab_id}, container={self.container_id})"


class ContainerTabManager:
    """Manages tab-container associations"""
    
    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
        self.tab_containers: Dict[int, str] = {}  # tab_id -> container_id
    
    def assign_container(self, tab_id: int, container_id: str):
        """Assign a tab to a container"""
        if container_id in self.container_manager.containers or container_id == "default":
            self.tab_containers[tab_id] = container_id
            log.info(f"Assigned tab {tab_id} to container {container_id}")
        else:
            log.warning(f"Container {container_id} not found")
    
    def get_container_for_tab(self, tab_id: int) -> Optional[str]:
        """Get the container ID for a tab"""
        return self.tab_containers.get(tab_id)
    
    def remove_tab(self, tab_id: int):
        """Remove tab from tracking"""
        if tab_id in self.tab_containers:
            del self.tab_containers[tab_id]
    
    def get_tabs_in_container(self, container_id: str) -> List[int]:
        """Get all tabs in a container"""
        return [
            tab_id for tab_id, cid in self.tab_containers.items()
            if cid == container_id
        ]
    
    def reopen_in_container(self, url: str, container_id: str) -> dict:
        """Get data for reopening URL in a different container"""
        return {
            "url": url,
            "container_id": container_id,
            "action": "reopen_in_container"
        }


class ContainerUI:
    """Helper for rendering container UI elements"""
    
    @staticmethod
    def get_container_indicator_html(container: Container) -> str:
        """Get HTML for container indicator"""
        return f"""
        <div class="container-indicator" style="
            background: {container.color};
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: white;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        ">
            <span>{container.icon}</span>
            <span>{container.name}</span>
        </div>
        """
    
    @staticmethod
    def get_container_badge_css(container: Container) -> str:
        """Get CSS for container badge on tab"""
        return f"""
        .tab-container-badge {{
            background: {container.color};
            width: 3px;
            height: 100%;
            position: absolute;
            left: 0;
            top: 0;
        }}
        
        .tab-container-badge::before {{
            content: '{container.icon}';
            position: absolute;
            left: 6px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 10px;
            color: {container.color};
        }}
        """
    
    @staticmethod
    def get_new_tab_menu_items(containers: List[Container]) -> List[dict]:
        """Get menu items for opening new tab in container"""
        items = [{"label": "New Tab (Default)", "container_id": "default"}]
        
        for container in containers:
            items.append({
                "label": f"New Tab in {container.icon} {container.name}",
                "container_id": container.id,
                "color": container.color,
            })
        
        return items
