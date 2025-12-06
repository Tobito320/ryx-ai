"""
PC Sync Service - Handles folder synchronization with PC
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from config import settings

logger = logging.getLogger(__name__)


class PCSyncService:
    """Service for syncing boards to PC folders"""

    def __init__(self):
        self.root_path = Path(settings.pc_sync_root)
        self._ensure_root_exists()

    def _ensure_root_exists(self):
        """Ensure root sync directory exists"""
        try:
            self.root_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ PC sync root initialized: {self.root_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create PC sync root: {e}")
            raise

    def _generate_folder_path(self, board) -> Path:
        """Generate folder path for a board"""
        # Create path: C:\FamilyDocs\2025\Dezember\BoardName
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%B")  # Full month name

        # Build hierarchy path
        path_parts = [year, month]

        # Add parent names if exists
        # TODO: Fetch parent names from database
        # For now, just use board name

        path_parts.append(self._sanitize_filename(board.name))

        folder_path = self.root_path / "/".join(path_parts)
        return folder_path

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")

        # Remove leading/trailing spaces and dots
        name = name.strip(). strip(".")

        # Limit length
        if len(name) > 200:
            name = name[:200]

        return name

    async def create_folder(self, board) -> str:
        """Create a folder on PC for a board"""
        try:
            folder_path = self._generate_folder_path(board)

            # Create folder
            folder_path.mkdir(parents=True, exist_ok=True)

            # Create a metadata file
            metadata_file = folder_path / ".familydocs_meta.json"
            import json
            metadata = {
                "board_id": str(board.id),
                "board_name": board.name,
                "created_at": datetime.now().isoformat(),
                "synced_at": datetime.now().isoformat(),
            }

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Created PC folder: {folder_path}")
            return str(folder_path)

        except Exception as e:
            logger.error(f"❌ Failed to create folder: {e}")
            raise

    async def archive_folder(self, pc_path: str):
        """Archive a folder (move to _archived subfolder)"""
        try:
            source_path = Path(pc_path)

            if not source_path.exists():
                logger.warning(f"⚠️ Folder does not exist: {pc_path}")
                return

            # Create _archived folder in same parent
            archive_dir = source_path.parent / "_archived"
            archive_dir.mkdir(exist_ok=True)

            # Move folder to archive with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"{source_path.name}_{timestamp}"

            shutil.move(str(source_path), str(archive_path))
            logger.info(f"✅ Archived folder: {source_path} -> {archive_path}")

        except Exception as e:
            logger.error(f"❌ Failed to archive folder: {e}")
            raise

    async def rename_folder(self, old_path: str, new_name: str) -> str:
        """Rename a folder"""
        try:
            old_path_obj = Path(old_path)

            if not old_path_obj.exists():
                logger.warning(f"⚠️ Folder does not exist: {old_path}")
                return old_path

            # Generate new path
            new_path = old_path_obj.parent / self._sanitize_filename(new_name)

            # Rename
            old_path_obj.rename(new_path)
            logger.info(f"✅ Renamed folder: {old_path} -> {new_path}")

            return str(new_path)

        except Exception as e:
            logger.error(f"❌ Failed to rename folder: {e}")
            raise

    async def watch_folder(self, pc_path: str):
        """Watch a folder for changes (for future implementation)"""
        # TODO: Implement with watchdog library
        # Monitor folder for:
        # - New files added -> trigger document upload
        # - Files deleted -> update board
        # - Folder renamed -> update board name
        pass
