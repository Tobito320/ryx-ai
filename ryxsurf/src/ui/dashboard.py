"""
RyxSurf Dashboard - Overview tab with metrics and quick access
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from datetime import datetime, timedelta
import json
from pathlib import Path


class DashboardView(Gtk.ScrolledWindow):
    """Dashboard overview page with metrics and quick access"""
    
    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Stats
        self.stats = self._load_stats()
        
        # Main container
        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.container.set_halign(Gtk.Align.CENTER)
        self.container.set_margin_top(40)
        self.container.set_margin_bottom(40)
        self.container.set_size_request(900, -1)
        
        self._build_ui()
        self.add(self.container)
        
        # Update stats every 5 seconds
        GLib.timeout_add_seconds(5, self._update_stats)
        
    def _load_stats(self):
        """Load stats from disk"""
        stats_file = Path.home() / ".config" / "ryxsurf" / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    return json.load(f)
            except:
                pass
        return {
            "ads_blocked": 0,
            "trackers_blocked": 0,
            "cookies_blocked": 0,
            "bandwidth_saved_mb": 0,
            "pages_loaded": 0,
            "time_saved_sec": 0,
            "start_date": datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save stats to disk"""
        stats_file = Path.home() / ".config" / "ryxsurf" / "stats.json"
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f)
    
    def _build_ui(self):
        """Build dashboard UI"""
        
        # Greeting
        greeting = self._create_greeting()
        self.container.pack_start(greeting, False, False, 20)
        
        # Stats grid
        stats_grid = self._create_stats_grid()
        self.container.pack_start(stats_grid, False, False, 10)
        
        # Quick access
        quick_access = self._create_quick_access()
        self.container.pack_start(quick_access, False, False, 20)
        
        # Recent sites
        recent = self._create_recent_sites()
        self.container.pack_start(recent, False, False, 10)
        
        # Bookmarks
        bookmarks = self._create_bookmarks_section()
        self.container.pack_start(bookmarks, False, False, 10)
        
    def _create_greeting(self):
        """Create greeting section"""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"
        
        label = Gtk.Label()
        label.set_markup(f'<span size="xx-large" weight="light">{greeting}</span>')
        label.set_halign(Gtk.Align.START)
        return label
    
    def _create_stats_grid(self):
        """Create stats grid"""
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(20)
        grid.set_halign(Gtk.Align.CENTER)
        
        stats = [
            ("🛡", "Ads Blocked", self.stats.get("ads_blocked", 0)),
            ("👁", "Trackers Blocked", self.stats.get("trackers_blocked", 0)),
            ("🍪", "Cookies Blocked", self.stats.get("cookies_blocked", 0)),
            ("💾", f"Bandwidth Saved", f"{self.stats.get('bandwidth_saved_mb', 0):.1f} MB"),
            ("📄", "Pages Loaded", self.stats.get("pages_loaded", 0)),
            ("⚡", "Time Saved", self._format_time(self.stats.get("time_saved_sec", 0))),
        ]
        
        col = 0
        row = 0
        for symbol, label, value in stats:
            card = self._create_stat_card(symbol, label, value)
            grid.attach(card, col, row, 1, 1)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        return grid
    
    def _create_stat_card(self, symbol, label, value):
        """Create individual stat card"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_size_request(280, 120)
        
        # Add subtle border and background
        card.set_margin_start(10)
        card.set_margin_end(10)
        card.set_margin_top(10)
        card.set_margin_bottom(10)
        
        style_context = card.get_style_context()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            box {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 20px;
            }
        """)
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Symbol
        symbol_label = Gtk.Label()
        symbol_label.set_markup(f'<span size="x-large">{symbol}</span>')
        symbol_label.set_halign(Gtk.Align.START)
        card.pack_start(symbol_label, False, False, 0)
        
        # Value
        value_label = Gtk.Label()
        value_label.set_markup(f'<span size="xx-large" weight="bold">{value}</span>')
        value_label.set_halign(Gtk.Align.START)
        card.pack_start(value_label, False, False, 0)
        
        # Label
        label_widget = Gtk.Label(label)
        label_widget.set_halign(Gtk.Align.START)
        label_widget.get_style_context().add_class("dim-label")
        card.pack_start(label_widget, False, False, 0)
        
        return card
    
    def _create_quick_access(self):
        """Create quick access section"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Title
        title = Gtk.Label()
        title.set_markup('<span size="large" weight="bold">Quick Access</span>')
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)
        
        # Buttons grid
        grid = Gtk.FlowBox()
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_max_children_per_line(6)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        
        quick_links = [
            ("🔍", "Search", "https://search.ryxsurf.local"),
            ("📧", "Email", "https://mail.google.com"),
            ("📺", "YouTube", "https://youtube.com"),
            ("🎵", "Music", "https://music.youtube.com"),
            ("💬", "Chat", "https://chat.openai.com"),
            ("📱", "Social", "https://twitter.com"),
            ("📰", "News", "https://news.ycombinator.com"),
            ("🛒", "Shopping", "https://amazon.com"),
        ]
        
        for symbol, label, url in quick_links:
            btn = self._create_quick_link(symbol, label, url)
            grid.add(btn)
        
        box.pack_start(grid, False, False, 0)
        return box
    
    def _create_quick_link(self, symbol, label, url):
        """Create quick link button"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_size_request(100, 80)
        
        btn = Gtk.Button()
        btn.add(box)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        
        # Symbol
        symbol_label = Gtk.Label()
        symbol_label.set_markup(f'<span size="x-large">{symbol}</span>')
        box.pack_start(symbol_label, True, True, 0)
        
        # Label
        label_widget = Gtk.Label(label)
        label_widget.get_style_context().add_class("dim-label")
        box.pack_start(label_widget, False, False, 0)
        
        btn.connect("clicked", lambda w: self.emit("navigate", url))
        return btn
    
    def _create_recent_sites(self):
        """Create recent sites section"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Title
        title = Gtk.Label()
        title.set_markup('<span size="large" weight="bold">Recent Sites</span>')
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)
        
        # List
        recent_list = Gtk.FlowBox()
        recent_list.set_selection_mode(Gtk.SelectionMode.NONE)
        recent_list.set_max_children_per_line(4)
        recent_list.set_column_spacing(10)
        recent_list.set_row_spacing(10)
        
        # Load from history
        recent = self._load_recent_sites()
        for site in recent[:8]:
            item = self._create_site_card(site)
            recent_list.add(item)
        
        box.pack_start(recent_list, False, False, 0)
        return box
    
    def _create_site_card(self, site):
        """Create site card"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_size_request(200, 50)
        
        btn = Gtk.Button()
        btn.add(box)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        
        # Favicon placeholder
        favicon = Gtk.Label()
        favicon.set_markup('<span size="large">🌐</span>')
        box.pack_start(favicon, False, False, 5)
        
        # Site info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        title = Gtk.Label(site.get("title", "Untitled"))
        title.set_ellipsize(3)  # END
        title.set_max_width_chars(20)
        title.set_halign(Gtk.Align.START)
        info_box.pack_start(title, False, False, 0)
        
        url = Gtk.Label(site.get("url", ""))
        url.set_ellipsize(3)
        url.set_max_width_chars(20)
        url.set_halign(Gtk.Align.START)
        url.get_style_context().add_class("dim-label")
        info_box.pack_start(url, False, False, 0)
        
        box.pack_start(info_box, True, True, 0)
        
        btn.connect("clicked", lambda w: self.emit("navigate", site.get("url", "")))
        return btn
    
    def _create_bookmarks_section(self):
        """Create bookmarks section"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Title
        title = Gtk.Label()
        title.set_markup('<span size="large" weight="bold">Bookmarks</span>')
        title.set_halign(Gtk.Align.START)
        box.pack_start(title, False, False, 0)
        
        # Bookmarks grid
        grid = Gtk.FlowBox()
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_max_children_per_line(4)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        
        bookmarks = self._load_bookmarks()
        for bookmark in bookmarks[:8]:
            item = self._create_site_card(bookmark)
            grid.add(item)
        
        box.pack_start(grid, False, False, 0)
        return box
    
    def _load_recent_sites(self):
        """Load recent sites from history"""
        history_file = Path.home() / ".config" / "ryxsurf" / "history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    history = json.load(f)
                    return sorted(history, key=lambda x: x.get("timestamp", 0), reverse=True)
            except:
                pass
        return []
    
    def _load_bookmarks(self):
        """Load bookmarks"""
        bookmarks_file = Path.home() / ".config" / "ryxsurf" / "bookmarks.json"
        if bookmarks_file.exists():
            try:
                with open(bookmarks_file) as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _format_time(self, seconds):
        """Format time in human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        else:
            return f"{seconds / 3600:.1f}h"
    
    def _update_stats(self):
        """Update stats display"""
        # This will be called periodically
        # Stats are updated by the browser when blocking occurs
        return True  # Continue timeout
    
    def increment_stat(self, stat_name, amount=1):
        """Increment a stat counter"""
        if stat_name in self.stats:
            self.stats[stat_name] += amount
            self._save_stats()
            # Rebuild UI to show new values
            GLib.idle_add(self._refresh_stats)
    
    def _refresh_stats(self):
        """Refresh stats display"""
        for child in self.container.get_children():
            self.container.remove(child)
        self._build_ui()
        self.show_all()


# Register custom signal
from gi.repository import GObject
GObject.signal_new("navigate", DashboardView, GObject.SignalFlags.RUN_FIRST, None, (str,))
