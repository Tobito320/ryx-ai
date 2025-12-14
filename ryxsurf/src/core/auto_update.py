"""
Auto Update System

Checks for and applies updates to RyxSurf.
"""

import logging
import json
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta

log = logging.getLogger("ryxsurf.update")


class Version:
    """Semantic version"""
    
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch
    
    @classmethod
    def from_string(cls, version_str: str):
        """Parse version from string"""
        parts = version_str.split('.')
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other):
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch
    
    def __eq__(self, other):
        return (self.major == other.major and 
                self.minor == other.minor and 
                self.patch == other.patch)
    
    def __le__(self, other):
        return self < other or self == other


class UpdateChecker:
    """Checks for browser updates"""
    
    CURRENT_VERSION = Version(0, 1, 0)
    UPDATE_CHECK_INTERVAL = timedelta(days=1)
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.update_file = config_dir / "update_info.json"
    
    def get_current_version(self) -> Version:
        """Get current browser version"""
        return self.CURRENT_VERSION
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Check if updates are available
        
        Returns:
            Dict with update info if available, None otherwise
        """
        # Check if we should check for updates
        if not self._should_check():
            log.debug("Skipping update check (checked recently)")
            return None
        
        try:
            # In a real implementation, this would query a remote server
            # For now, we'll just check a local file or return None
            
            # Simulate checking for updates
            available_version = self._get_available_version()
            
            if available_version and available_version > self.CURRENT_VERSION:
                update_info = {
                    "version": str(available_version),
                    "release_notes": self._get_release_notes(available_version),
                    "download_url": self._get_download_url(available_version),
                    "release_date": datetime.now().isoformat(),
                }
                
                log.info(f"Update available: {available_version}")
                return update_info
            
            log.debug("No updates available")
            self._save_last_check()
            return None
            
        except Exception as e:
            log.error(f"Failed to check for updates: {e}")
            return None
    
    def _should_check(self) -> bool:
        """Check if enough time has passed since last check"""
        if not self.update_file.exists():
            return True
        
        try:
            with open(self.update_file) as f:
                data = json.load(f)
            
            last_check = datetime.fromisoformat(data.get("last_check", ""))
            elapsed = datetime.now() - last_check
            
            return elapsed > self.UPDATE_CHECK_INTERVAL
        except Exception:
            return True
    
    def _save_last_check(self):
        """Save last check time"""
        data = {
            "last_check": datetime.now().isoformat(),
            "current_version": str(self.CURRENT_VERSION),
        }
        
        with open(self.update_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_available_version(self) -> Optional[Version]:
        """Get available version (placeholder)"""
        # In real implementation, fetch from update server
        # For now, return None (no updates)
        return None
    
    def _get_release_notes(self, version: Version) -> str:
        """Get release notes for version"""
        return f"Release notes for version {version}\n\n- New features\n- Bug fixes\n- Performance improvements"
    
    def _get_download_url(self, version: Version) -> str:
        """Get download URL for version"""
        return f"https://github.com/user/ryxsurf/releases/{version}"


class UpdateInstaller:
    """Installs browser updates"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def install_update(self, update_info: Dict) -> bool:
        """
        Install an update
        
        Args:
            update_info: Update information dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            version = update_info["version"]
            log.info(f"Installing update: {version}")
            
            # Download update
            if not self._download_update(update_info):
                return False
            
            # Verify update
            if not self._verify_update():
                log.error("Update verification failed")
                return False
            
            # Apply update
            if not self._apply_update():
                log.error("Failed to apply update")
                return False
            
            log.info(f"Successfully installed update: {version}")
            return True
            
        except Exception as e:
            log.error(f"Failed to install update: {e}")
            return False
    
    def _download_update(self, update_info: Dict) -> bool:
        """Download update package"""
        # Placeholder - would download from URL
        log.info("Downloading update...")
        return True
    
    def _verify_update(self) -> bool:
        """Verify update integrity"""
        # Placeholder - would verify checksums
        log.info("Verifying update...")
        return True
    
    def _apply_update(self) -> bool:
        """Apply the update"""
        # Placeholder - would extract and replace files
        log.info("Applying update...")
        return True


class UpdateNotifier:
    """Notifies user about updates"""
    
    def __init__(self):
        self.notification_shown = False
    
    def notify_update_available(self, update_info: Dict):
        """Show notification about available update"""
        if self.notification_shown:
            return
        
        version = update_info.get("version", "unknown")
        
        print("\n" + "="*60)
        print("🔔 UPDATE AVAILABLE")
        print("="*60)
        print(f"Version {version} is now available!")
        print("")
        print("Release Notes:")
        print(update_info.get("release_notes", "No release notes"))
        print("")
        print("To update:")
        print("  1. Close browser")
        print("  2. Run: cd ryxsurf && make update")
        print("  3. Restart browser")
        print("="*60 + "\n")
        
        self.notification_shown = True
    
    def notify_update_installed(self, version: str):
        """Show notification about installed update"""
        print("\n" + "="*60)
        print("✅ UPDATE INSTALLED")
        print("="*60)
        print(f"RyxSurf has been updated to version {version}")
        print("")
        print("Please restart the browser to use the new version.")
        print("="*60 + "\n")


class AutoUpdater:
    """Main auto-update coordinator"""
    
    def __init__(self, config_dir: Path, auto_install: bool = False):
        self.config_dir = config_dir
        self.auto_install = auto_install
        
        self.checker = UpdateChecker(config_dir)
        self.installer = UpdateInstaller(config_dir)
        self.notifier = UpdateNotifier()
    
    def check_and_notify(self):
        """Check for updates and notify if available"""
        update_info = self.checker.check_for_updates()
        
        if update_info:
            self.notifier.notify_update_available(update_info)
            
            if self.auto_install:
                if self.installer.install_update(update_info):
                    self.notifier.notify_update_installed(update_info["version"])
    
    def manual_update(self) -> bool:
        """Manually check and install updates"""
        print("🔍 Checking for updates...")
        
        update_info = self.checker.check_for_updates()
        
        if not update_info:
            print("✓ You are running the latest version")
            return False
        
        self.notifier.notify_update_available(update_info)
        
        # Ask for confirmation
        response = input("\nInstall update now? [y/N]: ").lower()
        
        if response == 'y':
            if self.installer.install_update(update_info):
                self.notifier.notify_update_installed(update_info["version"])
                return True
            else:
                print("❌ Update installation failed")
                return False
        else:
            print("Update cancelled")
            return False


def check_updates_background(config_dir: Path):
    """Check for updates in background (non-blocking)"""
    import threading
    
    def _check():
        try:
            updater = AutoUpdater(config_dir, auto_install=False)
            updater.check_and_notify()
        except Exception as e:
            log.error(f"Background update check failed: {e}")
    
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
