"""
Comprehensive Settings UI
Full settings panel with all browser configuration options.
Minimal design with symbols, organized categories.
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, GLib, Pango
from pathlib import Path
import logging

log = logging.getLogger("ryxsurf.settings_ui")


class SettingsWindow(Gtk.Window):
    """Comprehensive settings window"""
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        
        self.set_title("RyxSurf Settings")
        self.set_default_size(900, 700)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Setup settings UI"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(main_box)
        
        # Sidebar (categories)
        sidebar = self._create_sidebar()
        main_box.append(sidebar)
        
        # Content area
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.content_stack.set_hexpand(True)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.content_stack)
        main_box.append(scroll)
        
        # Create pages
        self._create_privacy_page()
        self._create_appearance_page()
        self._create_performance_page()
        self._create_browsing_page()
        self._create_advanced_page()
        self._create_experimental_page()
        self._create_shortcuts_page()
    
    def _create_sidebar(self):
        """Create settings sidebar"""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(200, -1)
        sidebar.add_css_class("sidebar")
        
        # Categories
        categories = [
            ("🔒", "Privacy & Security", "privacy"),
            ("🎨", "Appearance", "appearance"),
            ("⚡", "Performance", "performance"),
            ("🌐", "Browsing", "browsing"),
            ("🔧", "Advanced", "advanced"),
            ("🧪", "Experimental", "experimental"),
            ("⌨", "Keyboard", "shortcuts"),
        ]
        
        for icon, label, page_name in categories:
            btn = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            
            icon_label = Gtk.Label(label=icon)
            box.append(icon_label)
            
            text_label = Gtk.Label(label=label)
            text_label.set_xalign(0)
            text_label.set_hexpand(True)
            box.append(text_label)
            
            btn.set_child(box)
            btn.connect("clicked", lambda b, p=page_name: self.content_stack.set_visible_child_name(p))
            sidebar.append(btn)
        
        return sidebar
    
    def _create_privacy_page(self):
        """Privacy & Security settings"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        # Header
        header = Gtk.Label(label="Privacy & Security")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Tracking Protection
        section = self._create_section("Tracking Protection")
        
        tracking_combo = self._create_combo_row(
            "Protection Level",
            ["Off", "Standard", "Strict", "Custom"],
            1  # Default: Standard
        )
        section.append(tracking_combo)
        
        cookies_combo = self._create_combo_row(
            "Block Cookies",
            ["All", "Third-party", "None"],
            1  # Default: Third-party
        )
        section.append(cookies_combo)
        
        section.append(self._create_switch_row("Block Fingerprinting", True))
        section.append(self._create_switch_row("Block Cryptominers", True))
        
        page.append(section)
        
        # HTTPS
        section = self._create_section("HTTPS")
        section.append(self._create_switch_row("HTTPS-Only Mode", True))
        section.append(self._create_switch_row("Upgrade Mixed Content", True))
        page.append(section)
        
        # DNS
        section = self._create_section("DNS")
        section.append(self._create_switch_row("DNS over HTTPS", True))
        dns_combo = self._create_combo_row(
            "DNS Provider",
            ["Cloudflare", "Google", "Custom"],
            0
        )
        section.append(dns_combo)
        page.append(section)
        
        # Privacy
        section = self._create_section("Privacy")
        section.append(self._create_switch_row("Send Do Not Track", True))
        referrer_combo = self._create_combo_row(
            "Send Referrer",
            ["Always", "Same Origin", "Never"],
            1
        )
        section.append(referrer_combo)
        page.append(section)
        
        # Permissions
        section = self._create_section("Permissions")
        for perm in ["Location", "Camera", "Microphone", "Notifications"]:
            perm_combo = self._create_combo_row(
                perm,
                ["Allow", "Ask", "Deny"],
                1  # Default: Ask
            )
            section.append(perm_combo)
        page.append(section)
        
        self.content_stack.add_named(page, "privacy")
    
    def _create_appearance_page(self):
        """Appearance settings"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Appearance")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Theme
        section = self._create_section("Theme")
        theme_combo = self._create_combo_row(
            "Theme",
            ["Light", "Dark", "Auto"],
            1  # Default: Dark
        )
        section.append(theme_combo)
        
        color_btn = Gtk.Button(label="Choose Accent Color")
        section.append(color_btn)
        
        page.append(section)
        
        # Toolbar
        section = self._create_section("Toolbar")
        toolbar_combo = self._create_combo_row(
            "Toolbar Style",
            ["Minimal", "Compact", "Normal", "Spacious"],
            0  # Default: Minimal
        )
        section.append(toolbar_combo)
        
        section.append(self._create_switch_row("Show Bookmarks Bar", False))
        section.append(self._create_switch_row("Show Sidebar", True))
        
        sidebar_combo = self._create_combo_row(
            "Sidebar Position",
            ["Left", "Right"],
            0
        )
        section.append(sidebar_combo)
        
        page.append(section)
        
        # Tabs
        section = self._create_section("Tabs")
        tab_style = self._create_combo_row(
            "Tab Style",
            ["Compact", "Normal", "Vertical"],
            0
        )
        section.append(tab_style)
        
        section.append(self._create_switch_row("Show Tab Icons", True))
        page.append(section)
        
        # Fonts
        section = self._create_section("Fonts")
        font_combo = self._create_combo_row(
            "Font Family",
            ["System", "Serif", "Sans-serif", "Monospace"],
            0
        )
        section.append(font_combo)
        
        font_size = self._create_spin_row("Font Size", 9, 24, 14)
        section.append(font_size)
        
        page.append(section)
        
        # Display
        section = self._create_section("Display")
        section.append(self._create_switch_row("Compact Mode", True))
        section.append(self._create_switch_row("Animations", True))
        section.append(self._create_switch_row("Smooth Scrolling", True))
        page.append(section)
        
        self.content_stack.add_named(page, "appearance")
    
    def _create_performance_page(self):
        """Performance settings"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Performance")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Hardware Acceleration
        section = self._create_section("Hardware Acceleration")
        section.append(self._create_switch_row("Enable GPU", True))
        section.append(self._create_switch_row("Enable WebGL", True))
        section.append(self._create_switch_row("Enable WebGPU", True))
        page.append(section)
        
        # Memory Management
        section = self._create_section("Memory Management")
        section.append(self._create_switch_row("Tab Hibernation", True))
        
        timeout = self._create_spin_row("Hibernation Timeout (seconds)", 60, 3600, 300)
        section.append(timeout)
        
        max_tabs = self._create_spin_row("Max Active Tabs", 1, 50, 10)
        section.append(max_tabs)
        
        section.append(self._create_switch_row("Tab Discarding", True))
        
        page.append(section)
        
        # Cache
        section = self._create_section("Cache")
        disk_cache = self._create_spin_row("Disk Cache Size (MB)", 0, 10240, 1024)
        section.append(disk_cache)
        
        memory_cache = self._create_spin_row("Memory Cache Size (MB)", 0, 2048, 256)
        section.append(memory_cache)
        
        section.append(self._create_switch_row("Cache Compression", True))
        
        page.append(section)
        
        # Network
        section = self._create_section("Network")
        section.append(self._create_switch_row("Enable HTTP/2", True))
        section.append(self._create_switch_row("Enable HTTP/3", True))
        section.append(self._create_switch_row("Enable Prefetch", True))
        section.append(self._create_switch_row("Enable Prerender", False))
        page.append(section)
        
        # Resources
        section = self._create_section("Resources")
        section.append(self._create_switch_row("Lazy Load Images", True))
        section.append(self._create_switch_row("Lazy Load Iframes", True))
        section.append(self._create_switch_row("Limit Background Tabs", True))
        page.append(section)
        
        self.content_stack.add_named(page, "performance")
    
    def _create_browsing_page(self):
        """Browsing settings"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Browsing")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Homepage
        section = self._create_section("Homepage & New Tab")
        homepage_entry = Gtk.Entry()
        homepage_entry.set_text("http://localhost:8888")
        section.append(homepage_entry)
        
        new_tab_combo = self._create_combo_row(
            "New Tab Page",
            ["Blank", "Search", "Homepage", "Custom"],
            1
        )
        section.append(new_tab_combo)
        
        page.append(section)
        
        # Search
        section = self._create_section("Search")
        search_combo = self._create_combo_row(
            "Default Search Engine",
            ["SearXNG", "Google", "DuckDuckGo", "Brave"],
            0
        )
        section.append(search_combo)
        
        section.append(self._create_switch_row("Search Suggestions", True))
        section.append(self._create_switch_row("Search in URL Bar", True))
        
        page.append(section)
        
        # Navigation
        section = self._create_section("Navigation")
        section.append(self._create_switch_row("Enable Gestures", True))
        
        middle_click = self._create_combo_row(
            "Middle Click Action",
            ["New Tab", "Close Tab", "Paste & Go"],
            0
        )
        section.append(middle_click)
        
        page.append(section)
        
        # Downloads
        section = self._create_section("Downloads")
        download_entry = Gtk.Entry()
        download_entry.set_text("~/Downloads")
        section.append(download_entry)
        
        section.append(self._create_switch_row("Ask Download Location", False))
        section.append(self._create_switch_row("Auto Open Downloads", False))
        
        page.append(section)
        
        # History
        section = self._create_section("History")
        section.append(self._create_switch_row("Remember History", True))
        section.append(self._create_switch_row("Remember Downloads", True))
        
        retention = self._create_spin_row("History Retention (days)", 1, 365, 90)
        section.append(retention)
        
        page.append(section)
        
        self.content_stack.add_named(page, "browsing")
    
    def _create_advanced_page(self):
        """Advanced features"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Advanced Features")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Split View
        section = self._create_section("Split View")
        section.append(self._create_switch_row("Enable Split View", True))
        split_combo = self._create_combo_row(
            "Split Orientation",
            ["Horizontal", "Vertical", "Grid"],
            0
        )
        section.append(split_combo)
        page.append(section)
        
        # Tab Groups
        section = self._create_section("Tab Groups")
        section.append(self._create_switch_row("Enable Tab Groups", True))
        section.append(self._create_switch_row("Auto Group by Domain", False))
        page.append(section)
        
        # Sessions
        section = self._create_section("Sessions")
        section.append(self._create_switch_row("Enable Sessions", True))
        section.append(self._create_switch_row("Auto Save Sessions", True))
        page.append(section)
        
        # Reader Mode
        section = self._create_section("Reader Mode")
        section.append(self._create_switch_row("Enable Reader Mode", True))
        reader_font = self._create_combo_row(
            "Reader Font",
            ["Serif", "Sans-serif"],
            0
        )
        section.append(reader_font)
        page.append(section)
        
        # AI Integration
        section = self._create_section("AI Integration")
        section.append(self._create_switch_row("Enable AI", True))
        ai_provider = self._create_combo_row(
            "AI Provider",
            ["Local (Ollama)", "OpenAI", "Custom"],
            0
        )
        section.append(ai_provider)
        
        ai_model = Gtk.Entry()
        ai_model.set_text("qwen2.5:1.5b")
        ai_model.set_placeholder_text("AI Model")
        section.append(ai_model)
        
        page.append(section)
        
        self.content_stack.add_named(page, "advanced")
    
    def _create_experimental_page(self):
        """Experimental features"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Experimental Features")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        warning = Gtk.Label(label="⚠️ These features are experimental and may be unstable")
        warning.add_css_class("dim-label")
        warning.set_xalign(0)
        page.append(warning)
        
        # Resource Limiter
        section = self._create_section("Resource Limiter (Opera GX)")
        section.append(self._create_switch_row("Enable Resource Limiter", False))
        
        cpu = self._create_spin_row("CPU Limit (%)", 10, 100, 100)
        section.append(cpu)
        
        ram = self._create_spin_row("RAM Limit (MB)", 512, 16384, 4096)
        section.append(ram)
        
        page.append(section)
        
        # Ad Blocker
        section = self._create_section("Ad Blocker")
        section.append(self._create_switch_row("Enable Ad Blocker", False))
        page.append(section)
        
        # VPN
        section = self._create_section("VPN Integration")
        section.append(self._create_switch_row("Enable VPN", False))
        page.append(section)
        
        self.content_stack.add_named(page, "experimental")
    
    def _create_shortcuts_page(self):
        """Keyboard shortcuts"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        
        header = Gtk.Label(label="Keyboard Shortcuts")
        header.add_css_class("title-1")
        header.set_xalign(0)
        page.append(header)
        
        # Shortcuts list
        shortcuts = [
            ("Navigation", [
                ("Back", "Alt+Left"),
                ("Forward", "Alt+Right"),
                ("Reload", "Ctrl+R"),
                ("Home", "Alt+Home"),
            ]),
            ("Tabs", [
                ("New Tab", "Ctrl+T"),
                ("Close Tab", "Ctrl+W"),
                ("Next Tab", "Ctrl+Tab"),
                ("Previous Tab", "Ctrl+Shift+Tab"),
            ]),
            ("Page", [
                ("Find", "Ctrl+F"),
                ("Zoom In", "Ctrl++"),
                ("Zoom Out", "Ctrl+-"),
                ("Fullscreen", "F11"),
            ]),
        ]
        
        for category, items in shortcuts:
            section = self._create_section(category)
            
            for label, shortcut in items:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                row.set_margin_start(12)
                row.set_margin_end(12)
                row.set_margin_top(8)
                row.set_margin_bottom(8)
                
                label_widget = Gtk.Label(label=label)
                label_widget.set_xalign(0)
                label_widget.set_hexpand(True)
                row.append(label_widget)
                
                shortcut_label = Gtk.Label(label=shortcut)
                shortcut_label.add_css_class("dim-label")
                row.append(shortcut_label)
                
                section.append(row)
            
            page.append(section)
        
        self.content_stack.add_named(page, "shortcuts")
    
    def _create_section(self, title: str):
        """Create a settings section"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        label = Gtk.Label(label=title)
        label.add_css_class("title-4")
        label.set_xalign(0)
        label.set_margin_bottom(8)
        box.append(label)
        
        return box
    
    def _create_switch_row(self, label: str, default: bool = False):
        """Create a switch row"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.set_margin_start(12)
        row.set_margin_end(12)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_xalign(0)
        label_widget.set_hexpand(True)
        row.append(label_widget)
        
        switch = Gtk.Switch()
        switch.set_active(default)
        row.append(switch)
        
        return row
    
    def _create_combo_row(self, label: str, options: list, default: int = 0):
        """Create a combo box row"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_start(12)
        row.set_margin_end(12)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_xalign(0)
        label_widget.set_hexpand(True)
        row.append(label_widget)
        
        combo = Gtk.ComboBoxText()
        for option in options:
            combo.append_text(option)
        combo.set_active(default)
        row.append(combo)
        
        return row
    
    def _create_spin_row(self, label: str, min_val: int, max_val: int, default: int):
        """Create a spin button row"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_start(12)
        row.set_margin_end(12)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        label_widget = Gtk.Label(label=label)
        label_widget.set_xalign(0)
        label_widget.set_hexpand(True)
        row.append(label_widget)
        
        spin = Gtk.SpinButton()
        spin.set_range(min_val, max_val)
        spin.set_value(default)
        spin.set_increments(1, 10)
        row.append(spin)
        
        return row
    
    def _load_current_settings(self):
        """Load current settings into UI"""
        # TODO: Load actual settings values
        pass
    
    def _save_settings(self):
        """Save settings"""
        # TODO: Save settings
        self.settings.save()
        log.info("Settings saved")
