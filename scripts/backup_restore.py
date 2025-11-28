#!/usr/bin/env python3
"""
Ryx AI - Backup & Restore
Complete backup and restore functionality for Ryx AI data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import shutil
import tarfile
import json
from datetime import datetime
from typing import Dict, List, Any

from core.paths import get_project_root, get_data_dir, get_log_dir


class BackupRestore:
    """Backup and restore Ryx AI data"""

    def __init__(self) -> None:
        """Initialize backup/restore tool"""
        self.project_root = get_project_root()
        self.data_dir = get_data_dir()
        self.log_dir = get_log_dir()
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, include_logs: bool = False) -> Dict[str, Any]:
        """Create complete backup of Ryx AI data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"ryx_backup_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name

        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Creating Backup\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        print(f"\033[1;33mBackup location:\033[0m {backup_path}")
        print()

        files_to_backup = []

        # Include data directory
        if self.data_dir.exists():
            print("\033[1;33mCollecting data files...\033[0m")
            data_files = list(self.data_dir.rglob("*"))
            data_files = [f for f in data_files if f.is_file()]
            files_to_backup.extend(data_files)
            print(f"  \033[1;32m✓\033[0m Found {len(data_files)} data files")

        # Include logs if requested
        if include_logs and self.log_dir.exists():
            print("\n\033[1;33mCollecting log files...\033[0m")
            log_files = list(self.log_dir.rglob("*.log"))
            files_to_backup.extend(log_files)
            print(f"  \033[1;32m✓\033[0m Found {len(log_files)} log files")

        # Include config files
        print("\n\033[1;33mCollecting config files...\033[0m")
        config_dir = self.project_root / "configs"
        if config_dir.exists():
            config_files = list(config_dir.glob("*.json"))
            files_to_backup.extend(config_files)
            print(f"  \033[1;32m✓\033[0m Found {len(config_files)} config files")

        # Create tarball
        print(f"\n\033[1;33mCreating backup archive...\033[0m")

        total_size = 0
        with tarfile.open(backup_path, "w:gz") as tar:
            for file_path in files_to_backup:
                if file_path.exists():
                    # Store relative to project root
                    arcname = file_path.relative_to(self.project_root)
                    tar.add(file_path, arcname=arcname)
                    total_size += file_path.stat().st_size

        backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
        original_size_mb = total_size / (1024 * 1024)
        compression_ratio = (1 - backup_size_mb / original_size_mb) * 100 if original_size_mb > 0 else 0

        print(f"  \033[1;32m✓\033[0m Backup created successfully")
        print(f"  Files: {len(files_to_backup)}")
        print(f"  Original size: {original_size_mb:.2f} MB")
        print(f"  Backup size: {backup_size_mb:.2f} MB")
        print(f"  Compression: {compression_ratio:.1f}%")

        # Create backup manifest
        manifest = {
            'timestamp': timestamp,
            'backup_file': str(backup_path),
            'files_count': len(files_to_backup),
            'original_size_mb': original_size_mb,
            'backup_size_mb': backup_size_mb,
            'include_logs': include_logs
        }

        manifest_path = self.backup_dir / f"manifest_{timestamp}.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"\n\033[1;32m✓\033[0m Backup complete: {backup_path}")
        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return manifest

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Available Backups\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        backups = []

        # Find all backup files
        backup_files = sorted(self.backup_dir.glob("ryx_backup_*.tar.gz"), reverse=True)

        if not backup_files:
            print("\033[1;33m⚠\033[0m No backups found")
            print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")
            return []

        for i, backup_file in enumerate(backup_files, 1):
            # Extract timestamp from filename
            timestamp_str = backup_file.stem.replace("ryx_backup_", "")

            # Try to load manifest
            manifest_file = self.backup_dir / f"manifest_{timestamp_str}.json"
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    'timestamp': timestamp_str,
                    'backup_file': str(backup_file),
                    'backup_size_mb': backup_file.stat().st_size / (1024 * 1024)
                }

            backups.append(manifest)

            # Format timestamp for display
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                display_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                display_date = timestamp_str

            print(f"\033[1;33m{i}.\033[0m {display_date}")
            print(f"   File: {backup_file.name}")
            print(f"   Size: {manifest.get('backup_size_mb', 0):.2f} MB")
            if 'files_count' in manifest:
                print(f"   Files: {manifest['files_count']}")
            print()

        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        return backups

    def restore_backup(self, backup_file: Path, confirm: bool = False) -> Dict[str, Any]:
        """Restore from backup"""
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        if not confirm:
            print("\n\033[1;31m⚠ WARNING:\033[0m Restore will overwrite existing data!")
            print("Use --confirm to proceed with restore")
            return {'restored': False, 'reason': 'not_confirmed'}

        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Restoring Backup\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        print(f"\033[1;33mRestoring from:\033[0m {backup_file}")
        print()

        # Create backup of current state before restore
        print("\033[1;33mCreating safety backup of current state...\033[0m")
        safety_backup = self.create_backup(include_logs=False)
        print(f"  \033[1;32m✓\033[0m Safety backup: {safety_backup['backup_file']}")

        # Extract backup
        print(f"\n\033[1;33mExtracting backup...\033[0m")

        with tarfile.open(backup_file, "r:gz") as tar:
            members = tar.getmembers()
            print(f"  Extracting {len(members)} files...")

            # Extract to project root
            tar.extractall(self.project_root)

        print(f"  \033[1;32m✓\033[0m Restore completed successfully")
        print(f"\n\033[1;32m✓\033[0m Backup restored: {backup_file}")
        print(f"\n\033[1;33mNote:\033[0m Safety backup saved to: {safety_backup['backup_file']}")
        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return {
            'restored': True,
            'backup_file': str(backup_file),
            'safety_backup': safety_backup['backup_file']
        }

    def cleanup_old_backups(self, keep_count: int = 5) -> Dict[str, int]:
        """Remove old backups, keeping only the most recent ones"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print(f"\033[1;36mRyx AI - Cleanup Old Backups (Keep {keep_count})\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        # Find all backup files
        backup_files = sorted(self.backup_dir.glob("ryx_backup_*.tar.gz"), reverse=True)

        if len(backup_files) <= keep_count:
            print(f"\033[1;32m✓\033[0m Only {len(backup_files)} backups found, nothing to clean")
            print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")
            return {'removed': 0, 'space_freed_mb': 0}

        # Remove old backups
        to_remove = backup_files[keep_count:]
        removed = 0
        space_freed = 0

        for backup_file in to_remove:
            # Also remove manifest
            timestamp_str = backup_file.stem.replace("ryx_backup_", "")
            manifest_file = self.backup_dir / f"manifest_{timestamp_str}.json"

            space_freed += backup_file.stat().st_size

            backup_file.unlink()
            if manifest_file.exists():
                manifest_file.unlink()

            removed += 1
            print(f"  \033[1;32m✓\033[0m Removed: {backup_file.name}")

        space_freed_mb = space_freed / (1024 * 1024)

        print(f"\n\033[1;32m✓\033[0m Removed {removed} old backups")
        print(f"  Space freed: {space_freed_mb:.2f} MB")
        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return {'removed': removed, 'space_freed_mb': space_freed_mb}


def main():
    """Run backup/restore operations"""
    import argparse

    parser = argparse.ArgumentParser(description='Ryx AI Backup & Restore')
    parser.add_argument('action', choices=['create', 'list', 'restore', 'cleanup'],
                        help='Action to perform')
    parser.add_argument('--include-logs', action='store_true',
                        help='Include log files in backup')
    parser.add_argument('--backup-file', type=str,
                        help='Backup file to restore from')
    parser.add_argument('--confirm', action='store_true',
                        help='Confirm restore operation')
    parser.add_argument('--keep', type=int, default=5,
                        help='Number of backups to keep during cleanup (default: 5)')

    args = parser.parse_args()

    backup_tool = BackupRestore()

    if args.action == 'create':
        backup_tool.create_backup(include_logs=args.include_logs)
    elif args.action == 'list':
        backup_tool.list_backups()
    elif args.action == 'restore':
        if not args.backup_file:
            print("\033[1;31m✗\033[0m Error: --backup-file required for restore")
            sys.exit(1)
        backup_path = Path(args.backup_file)
        backup_tool.restore_backup(backup_path, confirm=args.confirm)
    elif args.action == 'cleanup':
        backup_tool.cleanup_old_backups(keep_count=args.keep)


if __name__ == "__main__":
    main()
