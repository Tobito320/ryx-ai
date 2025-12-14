"""
Parallel Download Manager

Download files using multiple connections for faster speeds.
"""

import logging
import threading
import time
import os
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
import hashlib

log = logging.getLogger("ryxsurf.downloads")


@dataclass
class DownloadChunk:
    """Download chunk info"""
    start: int
    end: int
    downloaded: int = 0
    completed: bool = False


@dataclass
class Download:
    """Download info"""
    url: str
    filename: str
    destination: Path
    size: int = 0
    downloaded: int = 0
    chunks: List[DownloadChunk] = field(default_factory=list)
    status: str = "pending"  # pending, downloading, paused, completed, error
    error: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    speed: float = 0.0  # bytes per second
    
    def get_progress(self) -> float:
        """Get download progress (0-1)"""
        if self.size == 0:
            return 0.0
        return self.downloaded / self.size
    
    def get_eta(self) -> float:
        """Get estimated time remaining (seconds)"""
        if self.speed == 0 or self.downloaded == 0:
            return 0.0
        remaining = self.size - self.downloaded
        return remaining / self.speed


class ParallelDownloadManager:
    """Parallel download manager"""
    
    def __init__(
        self,
        max_connections: int = 8,
        chunk_size: int = 1024 * 1024,  # 1MB
        max_concurrent: int = 3,
    ):
        self.max_connections = max_connections
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        
        self.downloads: Dict[str, Download] = {}
        self.active_downloads: List[str] = []
        self.queue: List[str] = []
        
        self._lock = threading.Lock()
        self._enabled = True
        
        # Callbacks
        self.progress_callback: Optional[Callable] = None
        self.complete_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        log.info(f"Parallel download manager initialized ({max_connections} connections)")
    
    def add_download(
        self,
        url: str,
        destination: Path,
        filename: Optional[str] = None,
    ) -> str:
        """Add download to queue"""
        # Generate download ID
        download_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]
        
        # Determine filename
        if not filename:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "download"
        
        # Create download
        download = Download(
            url=url,
            filename=filename,
            destination=destination / filename,
            status="pending",
        )
        
        with self._lock:
            self.downloads[download_id] = download
            self.queue.append(download_id)
        
        log.info(f"Added download: {filename} ({download_id})")
        
        # Start if not at concurrent limit
        self._process_queue()
        
        return download_id
    
    def start_download(self, download_id: str) -> bool:
        """Start a download"""
        with self._lock:
            if download_id not in self.downloads:
                return False
            
            download = self.downloads[download_id]
            
            if download.status == "downloading":
                return True
            
            # Check concurrent limit
            if len(self.active_downloads) >= self.max_concurrent:
                if download_id not in self.queue:
                    self.queue.append(download_id)
                return False
            
            download.status = "downloading"
            download.start_time = time.time()
            self.active_downloads.append(download_id)
        
        # Start download in background
        threading.Thread(
            target=self._download_file,
            args=(download_id,),
            daemon=True
        ).start()
        
        log.info(f"Started download: {download.filename}")
        return True
    
    def pause_download(self, download_id: str) -> bool:
        """Pause a download"""
        with self._lock:
            if download_id not in self.downloads:
                return False
            
            download = self.downloads[download_id]
            
            if download.status == "downloading":
                download.status = "paused"
                log.info(f"Paused download: {download.filename}")
                return True
        
        return False
    
    def resume_download(self, download_id: str) -> bool:
        """Resume a paused download"""
        with self._lock:
            if download_id not in self.downloads:
                return False
            
            download = self.downloads[download_id]
            
            if download.status == "paused":
                download.status = "pending"
                if download_id not in self.queue:
                    self.queue.append(download_id)
                
                log.info(f"Resumed download: {download.filename}")
        
        self._process_queue()
        return True
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download"""
        with self._lock:
            if download_id not in self.downloads:
                return False
            
            download = self.downloads[download_id]
            download.status = "cancelled"
            
            # Remove from queue and active
            if download_id in self.queue:
                self.queue.remove(download_id)
            if download_id in self.active_downloads:
                self.active_downloads.remove(download_id)
            
            # Delete partial file
            if download.destination.exists():
                try:
                    download.destination.unlink()
                except:
                    pass
            
            log.info(f"Cancelled download: {download.filename}")
        
        self._process_queue()
        return True
    
    def get_download(self, download_id: str) -> Optional[Download]:
        """Get download info"""
        return self.downloads.get(download_id)
    
    def get_all_downloads(self) -> List[Download]:
        """Get all downloads"""
        return list(self.downloads.values())
    
    def get_active_downloads(self) -> List[Download]:
        """Get active downloads"""
        return [self.downloads[did] for did in self.active_downloads if did in self.downloads]
    
    def _download_file(self, download_id: str):
        """Download file with parallel connections (mock implementation)"""
        with self._lock:
            if download_id not in self.downloads:
                return
            download = self.downloads[download_id]
        
        try:
            # Mock download - in real implementation, this would:
            # 1. HEAD request to get size and check if server supports ranges
            # 2. Split into chunks
            # 3. Download chunks in parallel
            # 4. Combine chunks
            
            # For now, just simulate
            total_size = 10 * 1024 * 1024  # 10MB mock
            download.size = total_size
            
            # Simulate download in chunks
            chunk_count = 10
            chunk_size = total_size // chunk_count
            
            for i in range(chunk_count):
                with self._lock:
                    if download.status != "downloading":
                        break
                
                # Simulate chunk download
                time.sleep(0.1)
                
                with self._lock:
                    download.downloaded += chunk_size
                    elapsed = time.time() - download.start_time
                    download.speed = download.downloaded / elapsed if elapsed > 0 else 0
                
                # Progress callback
                if self.progress_callback:
                    self.progress_callback(download_id, download.get_progress())
            
            # Complete
            with self._lock:
                download.status = "completed"
                download.end_time = time.time()
                download.downloaded = download.size
                
                if download_id in self.active_downloads:
                    self.active_downloads.remove(download_id)
            
            log.info(f"Completed download: {download.filename}")
            
            # Complete callback
            if self.complete_callback:
                self.complete_callback(download_id)
            
            # Process queue
            self._process_queue()
        
        except Exception as e:
            with self._lock:
                download.status = "error"
                download.error = str(e)
                
                if download_id in self.active_downloads:
                    self.active_downloads.remove(download_id)
            
            log.error(f"Download failed: {download.filename} - {e}")
            
            # Error callback
            if self.error_callback:
                self.error_callback(download_id, str(e))
            
            # Process queue
            self._process_queue()
    
    def _process_queue(self):
        """Process download queue"""
        with self._lock:
            while len(self.active_downloads) < self.max_concurrent and len(self.queue) > 0:
                download_id = self.queue.pop(0)
                self.start_download(download_id)
    
    def get_stats(self) -> Dict:
        """Get download statistics"""
        with self._lock:
            total_downloads = len(self.downloads)
            active = len(self.active_downloads)
            queued = len(self.queue)
            
            completed = sum(1 for d in self.downloads.values() if d.status == "completed")
            failed = sum(1 for d in self.downloads.values() if d.status == "error")
            
            total_speed = sum(d.speed for d in self.downloads.values() if d.status == "downloading")
            
            return {
                "total_downloads": total_downloads,
                "active_downloads": active,
                "queued_downloads": queued,
                "completed_downloads": completed,
                "failed_downloads": failed,
                "total_speed_mbps": (total_speed / (1024 * 1024)),
                "max_connections": self.max_connections,
                "max_concurrent": self.max_concurrent,
            }
    
    def clear_completed(self):
        """Clear completed downloads"""
        with self._lock:
            to_remove = [
                did for did, d in self.downloads.items()
                if d.status in ("completed", "error", "cancelled")
            ]
            
            for did in to_remove:
                del self.downloads[did]
            
            log.info(f"Cleared {len(to_remove)} completed downloads")


def create_download_manager(**kwargs) -> ParallelDownloadManager:
    """Create parallel download manager"""
    return ParallelDownloadManager(**kwargs)
