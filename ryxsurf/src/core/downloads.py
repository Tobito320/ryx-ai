"""
RyxSurf Download Manager

Handles file downloads with:
- Progress tracking
- Download queue management
- Notifications
- Resume capability
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, WebKit, GLib, Gio
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
import threading


class DownloadState(Enum):
    """Download states"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadInfo:
    """Information about a download"""
    id: str
    url: str
    filename: str
    destination: Path
    state: DownloadState = DownloadState.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    bytes_received: int = 0
    total_bytes: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    webkit_download: Optional[WebKit.Download] = None


class DownloadManager:
    """
    Manages file downloads.
    
    Features:
    - Automatic download directory (~/Downloads)
    - Progress tracking
    - Download notification UI
    - Pause/resume/cancel
    """
    
    def __init__(
        self,
        download_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[DownloadInfo], None]] = None,
        on_complete: Optional[Callable[[DownloadInfo], None]] = None,
        on_failed: Optional[Callable[[DownloadInfo], None]] = None
    ):
        self.download_dir = download_dir or Path.home() / "Downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_failed = on_failed
        
        self.downloads: Dict[str, DownloadInfo] = {}
        self._download_counter = 0
        self._lock = threading.Lock()
        
    def setup_webview(self, webview: WebKit.WebView):
        """Connect download handling to a WebView"""
        # Get the WebContext to handle download decisions
        context = webview.get_network_session().get_website_data_manager()
        
        # Connect to decide-destination signal via WebView
        webview.connect("decide-policy", self._on_decide_policy)
        
    def _on_decide_policy(self, webview, decision, decision_type):
        """Handle navigation policy decisions including downloads"""
        if decision_type == WebKit.PolicyDecisionType.RESPONSE:
            response = decision.get_response()
            if response:
                mime = response.get_mime_type()
                # Check if this should be a download
                if self._should_download(response):
                    decision.download()
                    return True
        return False
        
    def _should_download(self, response) -> bool:
        """Determine if response should be downloaded"""
        mime = response.get_mime_type() or ""
        
        # Common download MIME types
        download_mimes = [
            "application/octet-stream",
            "application/zip",
            "application/x-tar",
            "application/x-gzip",
            "application/pdf",
            "application/x-7z-compressed",
            "application/x-rar-compressed",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats",
            "application/msword",
            "video/",
            "audio/",
            "image/",
        ]
        
        for dm in download_mimes:
            if dm in mime:
                return True
                
        # Check Content-Disposition header
        # Note: This requires checking response headers which may not be directly available
        
        return False
        
    def handle_download(self, download: WebKit.Download) -> DownloadInfo:
        """Handle a new download from WebKit"""
        with self._lock:
            self._download_counter += 1
            download_id = f"dl_{self._download_counter}"
        
        # Get URL and suggested filename
        request = download.get_request()
        url = request.get_uri() if request else "unknown"
        
        # Connect to signals
        download.connect("decide-destination", self._on_decide_destination)
        download.connect("received-data", self._on_received_data)
        download.connect("finished", self._on_finished)
        download.connect("failed", self._on_download_failed)
        
        # Create download info (filename will be set in decide-destination)
        info = DownloadInfo(
            id=download_id,
            url=url,
            filename="downloading...",
            destination=self.download_dir / "downloading",
            state=DownloadState.PENDING,
            webkit_download=download
        )
        
        self.downloads[download_id] = info
        return info
        
    def _on_decide_destination(self, download, suggested_filename):
        """Called when download destination needs to be decided"""
        # Find the download info
        info = self._find_download(download)
        if not info:
            return False
            
        # Set filename and destination
        filename = suggested_filename or "download"
        destination = self._get_unique_path(self.download_dir / filename)
        
        info.filename = destination.name
        info.destination = destination
        info.state = DownloadState.DOWNLOADING
        
        # Set the destination URI
        download.set_destination(destination.as_uri())
        
        # Allow download
        return True
        
    def _on_received_data(self, download, data_length):
        """Called when download data is received"""
        info = self._find_download(download)
        if not info:
            return
            
        # Update progress
        info.bytes_received = download.get_received_data_length()
        response = download.get_response()
        if response:
            info.total_bytes = response.get_content_length()
            
        if info.total_bytes > 0:
            info.progress = info.bytes_received / info.total_bytes
        else:
            info.progress = 0.0
            
        # Notify
        if self.on_progress:
            GLib.idle_add(self.on_progress, info)
            
    def _on_finished(self, download):
        """Called when download completes"""
        info = self._find_download(download)
        if not info:
            return
            
        info.state = DownloadState.COMPLETED
        info.progress = 1.0
        info.completed_at = datetime.now()
        
        if self.on_complete:
            GLib.idle_add(self.on_complete, info)
            
    def _on_download_failed(self, download, error):
        """Called when download fails"""
        info = self._find_download(download)
        if not info:
            return
            
        info.state = DownloadState.FAILED
        info.error_message = str(error) if error else "Unknown error"
        
        if self.on_failed:
            GLib.idle_add(self.on_failed, info)
            
    def _find_download(self, webkit_download: WebKit.Download) -> Optional[DownloadInfo]:
        """Find DownloadInfo by WebKit download object"""
        for info in self.downloads.values():
            if info.webkit_download == webkit_download:
                return info
        return None
        
    def _get_unique_path(self, path: Path) -> Path:
        """Get unique path by adding number suffix if exists"""
        if not path.exists():
            return path
            
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem} ({counter}){suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
            
    def cancel(self, download_id: str):
        """Cancel a download"""
        if download_id in self.downloads:
            info = self.downloads[download_id]
            if info.webkit_download and info.state == DownloadState.DOWNLOADING:
                info.webkit_download.cancel()
                info.state = DownloadState.CANCELLED
                
    def get_active_downloads(self) -> List[DownloadInfo]:
        """Get list of active (non-completed) downloads"""
        return [
            d for d in self.downloads.values()
            if d.state in (DownloadState.PENDING, DownloadState.DOWNLOADING, DownloadState.PAUSED)
        ]
        
    def get_completed_downloads(self) -> List[DownloadInfo]:
        """Get list of completed downloads"""
        return [d for d in self.downloads.values() if d.state == DownloadState.COMPLETED]
        
    def clear_completed(self):
        """Clear completed downloads from list"""
        self.downloads = {
            k: v for k, v in self.downloads.items()
            if v.state not in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.FAILED)
        }
        
    def get_stats(self) -> dict:
        """Get download statistics"""
        active = self.get_active_downloads()
        completed = self.get_completed_downloads()
        
        total_progress = sum(d.progress for d in active) / len(active) if active else 0
        
        return {
            "active_count": len(active),
            "completed_count": len(completed),
            "total_progress": total_progress,
            "total_bytes_received": sum(d.bytes_received for d in active)
        }


class DownloadNotification(Gtk.Box):
    """
    Small notification widget showing download progress.
    
    Displayed at bottom of browser window.
    """
    
    def __init__(self, download_manager: DownloadManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.download_manager = download_manager
        self.add_css_class("download-notification")
        
        # Connect to download events
        download_manager.on_progress = self._on_progress
        download_manager.on_complete = self._on_complete
        download_manager.on_failed = self._on_failed
        
        self._setup_ui()
        self._apply_css()
        self.set_visible(False)
        
    def _setup_ui(self):
        """Setup notification UI"""
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_bottom(20)
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.END)
        
        # Container for download items
        self.items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.append(self.items_box)
        
    def _on_progress(self, info: DownloadInfo):
        """Update progress for a download"""
        self.set_visible(True)
        self._update_item(info)
        
    def _on_complete(self, info: DownloadInfo):
        """Handle download completion"""
        self._update_item(info)
        # Auto-hide after 5 seconds if no active downloads
        GLib.timeout_add(5000, self._check_hide)
        
    def _on_failed(self, info: DownloadInfo):
        """Handle download failure"""
        self._update_item(info)
        
    def _update_item(self, info: DownloadInfo):
        """Update or create download item widget"""
        # Find existing or create new
        item_widget = None
        for child in self._get_children():
            if hasattr(child, 'download_id') and child.download_id == info.id:
                item_widget = child
                break
                
        if not item_widget:
            item_widget = self._create_item(info)
            self.items_box.append(item_widget)
        else:
            self._update_item_widget(item_widget, info)
            
    def _create_item(self, info: DownloadInfo) -> Gtk.Box:
        """Create a download item widget"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.download_id = info.id
        box.add_css_class("download-item")
        
        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        filename_label = Gtk.Label(label=info.filename[:40])
        filename_label.set_halign(Gtk.Align.START)
        filename_label.set_hexpand(True)
        filename_label.add_css_class("download-filename")
        header.append(filename_label)
        
        status_label = Gtk.Label()
        status_label.add_css_class("download-status")
        header.append(status_label)
        
        box.append(header)
        
        # Progress bar
        progress = Gtk.ProgressBar()
        progress.add_css_class("download-progress")
        box.append(progress)
        
        # Store references
        box.filename_label = filename_label
        box.status_label = status_label
        box.progress_bar = progress
        
        self._update_item_widget(box, info)
        return box
        
    def _update_item_widget(self, widget: Gtk.Box, info: DownloadInfo):
        """Update an existing item widget"""
        widget.filename_label.set_text(info.filename[:40])
        widget.progress_bar.set_fraction(info.progress)
        
        if info.state == DownloadState.COMPLETED:
            widget.status_label.set_text("✓ Done")
            widget.status_label.add_css_class("completed")
        elif info.state == DownloadState.FAILED:
            widget.status_label.set_text("✗ Failed")
            widget.status_label.add_css_class("failed")
        elif info.state == DownloadState.DOWNLOADING:
            if info.total_bytes > 0:
                mb_received = info.bytes_received / (1024 * 1024)
                mb_total = info.total_bytes / (1024 * 1024)
                widget.status_label.set_text(f"{mb_received:.1f}/{mb_total:.1f} MB")
            else:
                kb = info.bytes_received / 1024
                widget.status_label.set_text(f"{kb:.0f} KB")
                
    def _get_children(self):
        """Get all child widgets"""
        children = []
        child = self.items_box.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()
        return children
        
    def _check_hide(self) -> bool:
        """Check if notification should be hidden"""
        active = self.download_manager.get_active_downloads()
        if not active:
            # Clear completed and hide
            for child in self._get_children():
                self.items_box.remove(child)
            self.set_visible(False)
        return False  # Don't repeat
        
    def _apply_css(self):
        """Apply notification styling"""
        css = b"""
        .download-notification {
            background: rgba(40, 42, 54, 0.95);
            border-radius: 8px;
            padding: 12px;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            border: 1px solid #44475a;
        }
        
        .download-item {
            padding: 8px;
            border-radius: 4px;
            background: rgba(68, 71, 90, 0.5);
        }
        
        .download-filename {
            color: #f8f8f2;
            font-size: 13px;
        }
        
        .download-status {
            color: #6272a4;
            font-size: 12px;
        }
        
        .download-status.completed {
            color: #50fa7b;
        }
        
        .download-status.failed {
            color: #ff5555;
        }
        
        .download-progress {
            min-height: 4px;
            border-radius: 2px;
        }
        
        .download-progress progress {
            background: #bd93f9;
            border-radius: 2px;
        }
        
        .download-progress trough {
            background: #44475a;
            border-radius: 2px;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        
        from gi.repository import Gdk
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
