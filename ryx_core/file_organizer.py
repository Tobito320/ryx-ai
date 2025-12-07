"""
File Organizer for RyxHub
AI-powered file organization and management
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import re


DOCUMENTS_PATH = Path("/home/tobi/documents")

# Category definitions with keywords
CATEGORIES = {
    "familie": {
        "keywords": ["familie", "wohnung", "miete", "mietvertrag", "hausverwaltung", "nachbar"],
        "path": DOCUMENTS_PATH / "familie",
    },
    "aok": {
        "keywords": ["aok", "krankenkasse", "krankenversicherung", "gesundheit", "arzt", "rezept"],
        "path": DOCUMENTS_PATH / "aok",
    },
    "sparkasse": {
        "keywords": ["sparkasse", "bank", "konto", "überweisung", "kontoauszug", "kredit"],
        "path": DOCUMENTS_PATH / "sparkasse",
    },
    "auto": {
        "keywords": ["auto", "kfz", "tüv", "versicherung", "führerschein", "werkstatt", "fahrzeug"],
        "path": DOCUMENTS_PATH / "auto",
    },
    "azubi": {
        "keywords": ["azubi", "ausbildung", "berufsschule", "ihk", "ausbilder", "praktikum"],
        "path": DOCUMENTS_PATH / "azubi",
    },
    "arbeit": {
        "keywords": ["arbeit", "arbeitgeber", "lohn", "gehalt", "arbeitsvertrag", "kündigung"],
        "path": DOCUMENTS_PATH / "arbeit",
    },
}


class FileOrganizer:
    def __init__(self):
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all category directories exist"""
        for cat_info in CATEGORIES.values():
            cat_info["path"].mkdir(parents=True, exist_ok=True)
    
    def categorize_by_name(self, filename: str) -> str:
        """Categorize file by filename"""
        filename_lower = filename.lower()
        
        for category, info in CATEGORIES.items():
            for keyword in info["keywords"]:
                if keyword in filename_lower:
                    return category
        
        return "other"
    
    def categorize_by_content(self, text: str) -> str:
        """Categorize file by content analysis"""
        text_lower = text.lower()
        
        scores = {}
        for category, info in CATEGORIES.items():
            score = 0
            for keyword in info["keywords"]:
                score += text_lower.count(keyword)
            scores[category] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return "other"
    
    def suggest_filename(self, original: str, content_summary: str = None) -> str:
        """Suggest a better filename based on content"""
        # Remove date prefixes like "20251114-180801"
        clean = re.sub(r'^\d{8}[-_]?\d*[-_]?', '', original)
        
        # If we have content summary, use that
        if content_summary:
            # Take first 50 chars of summary
            suggested = content_summary[:50].strip()
            # Clean for filename
            suggested = re.sub(r'[^\w\s-]', '', suggested)
            suggested = suggested.replace(' ', '_')
            
            # Get extension from original
            ext = Path(original).suffix
            if ext:
                suggested = f"{suggested}{ext}"
            return suggested
        
        return clean if clean else original
    
    def move_to_category(
        self,
        source_path: str,
        category: str,
        new_name: str = None
    ) -> Tuple[bool, str]:
        """Move file to category folder"""
        source = Path(source_path)
        
        if not source.exists():
            return False, f"Source file not found: {source}"
        
        if category not in CATEGORIES:
            return False, f"Unknown category: {category}"
        
        dest_dir = CATEGORIES[category]["path"]
        dest_name = new_name if new_name else source.name
        dest_path = dest_dir / dest_name
        
        # Handle duplicates
        counter = 1
        while dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        try:
            shutil.move(str(source), str(dest_path))
            return True, str(dest_path)
        except Exception as e:
            return False, str(e)
    
    def copy_to_category(
        self,
        source_path: str,
        category: str,
        new_name: str = None
    ) -> Tuple[bool, str]:
        """Copy file to category folder"""
        source = Path(source_path)
        
        if not source.exists():
            return False, f"Source file not found: {source}"
        
        if category not in CATEGORIES:
            return False, f"Unknown category: {category}"
        
        dest_dir = CATEGORIES[category]["path"]
        dest_name = new_name if new_name else source.name
        dest_path = dest_dir / dest_name
        
        # Handle duplicates
        counter = 1
        while dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        try:
            shutil.copy2(str(source), str(dest_path))
            return True, str(dest_path)
        except Exception as e:
            return False, str(e)
    
    def create_folder(self, parent: str, name: str) -> Tuple[bool, str]:
        """Create a new folder"""
        parent_path = Path(parent)
        if not parent_path.exists():
            return False, f"Parent folder not found: {parent}"
        
        new_folder = parent_path / name
        try:
            new_folder.mkdir(parents=True, exist_ok=True)
            return True, str(new_folder)
        except Exception as e:
            return False, str(e)
    
    def rename_file(self, path: str, new_name: str) -> Tuple[bool, str]:
        """Rename a file"""
        source = Path(path)
        if not source.exists():
            return False, f"File not found: {path}"
        
        dest = source.parent / new_name
        try:
            source.rename(dest)
            return True, str(dest)
        except Exception as e:
            return False, str(e)
    
    def delete_file(self, path: str) -> Tuple[bool, str]:
        """Delete a file (move to trash)"""
        source = Path(path)
        if not source.exists():
            return False, f"File not found: {path}"
        
        # Move to trash folder instead of permanent delete
        trash_dir = DOCUMENTS_PATH / ".trash"
        trash_dir.mkdir(exist_ok=True)
        
        trash_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source.name}"
        trash_path = trash_dir / trash_name
        
        try:
            shutil.move(str(source), str(trash_path))
            return True, f"Moved to trash: {trash_path}"
        except Exception as e:
            return False, str(e)
    
    def get_folder_stats(self) -> Dict[str, Dict]:
        """Get statistics for each category folder"""
        stats = {}
        
        for category, info in CATEGORIES.items():
            path = info["path"]
            if path.exists():
                files = list(path.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                stats[category] = {
                    "path": str(path),
                    "file_count": len([f for f in files if f.is_file()]),
                    "folder_count": len([f for f in files if f.is_dir()]),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                }
            else:
                stats[category] = {
                    "path": str(path),
                    "file_count": 0,
                    "folder_count": 0,
                    "total_size_mb": 0,
                }
        
        return stats
    
    def get_uncategorized(self) -> List[Dict]:
        """Get files in root documents folder (uncategorized)"""
        files = []
        
        for item in DOCUMENTS_PATH.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    "suggested_category": self.categorize_by_name(item.name),
                })
        
        return files


# Singleton instance
file_organizer = FileOrganizer()
