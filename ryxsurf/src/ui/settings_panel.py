"""
Comprehensive Settings Panel for RyxSurf

Minimal, calm design with symbols instead of emojis.
Organized into categories with clean search functionality.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from typing import Callable, Optional, Any
import logging

log = logging.getLogger("ryxsurf.settings_panel")


class SettingsPanel(Gtk.Box):
    """Main settings panel with category sidebar"""
    
    def __init__(self, settings_manager, on_close: Callable):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.settings = settings_manager
        self.on_close = on_close
        
        self.add_css_class("settings-panel")
        
        # Left sidebar with categories
        self._create_sidebar()
        
        # Right content area
        self._create_content_area()
        
        # Show first category
        self._show_category("appearance")
    
    def _create_sidebar(self):
        """Create left sidebar with category list"""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("settings-sidebar")
        sidebar.set_size_request(200, -1)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("settings-header")
        header.set_spacing(8)
        
        title = Gtk.Label(label="Settings")
        title.add_css_class("settings-title")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)
        
        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("close-btn")
        close_btn.connect("clicked", lambda _: self.on_close())
        header.append(close_btn)
        
        sidebar.append(header)
        
        # Search bar
        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search settings...")
        search.add_css_class("settings-search")
        search.connect("search-changed", self._on_search)
        sidebar.append(search)
        
        # Category list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        self.category_list = Gtk.ListBox()
        self.category_list.add_css_class("category-list")
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.connect("row-activated", self._on_category_selected)
        
        categories = [
            ("appearance", "◐", "Appearance"),
            ("privacy", "◈", "Privacy & Security"),
            ("performance", "◎", "Performance"),
            ("content", "▣", "Content"),
            ("search", "◉", "Search"),
            ("workspace", "▦", "Workspaces"),
            ("tabs", "▥", "Tabs"),
            ("session", "◫", "Session"),
            ("downloads", "▾", "Downloads"),
            ("developer", "◬", "Developer"),
            ("sync", "◭", "Sync"),
            ("accessibility", "◮", "Accessibility"),
        ]
        
        for cat_id, icon, label in categories:
            row = self._create_category_row(cat_id, icon, label)
            self.category_list.append(row)
        
        scroll.set_child(self.category_list)
        sidebar.append(scroll)
        
        # Footer with export/import
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        footer.add_css_class("settings-footer")
        footer.set_spacing(4)
        
        export_btn = Gtk.Button(label="Export")
        export_btn.add_css_class("footer-btn")
        export_btn.connect("clicked", lambda _: self._export_settings())
        footer.append(export_btn)
        
        import_btn = Gtk.Button(label="Import")
        import_btn.add_css_class("footer-btn")
        import_btn.connect("clicked", lambda _: self._import_settings())
        footer.append(import_btn)
        
        reset_btn = Gtk.Button(label="Reset")
        reset_btn.add_css_class("footer-btn")
        reset_btn.connect("clicked", lambda _: self._reset_settings())
        footer.append(reset_btn)
        
        sidebar.append(footer)
        
        self.append(sidebar)
    
    def _create_category_row(self, cat_id: str, icon: str, label: str) -> Gtk.ListBoxRow:
        """Create a category list row"""
        row = Gtk.ListBoxRow()
        row.category_id = cat_id
        row.add_css_class("category-row")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        
        icon_label = Gtk.Label(label=icon)
        icon_label.add_css_class("category-icon")
        box.append(icon_label)
        
        text = Gtk.Label(label=label)
        text.add_css_class("category-label")
        text.set_halign(Gtk.Align.START)
        text.set_hexpand(True)
        box.append(text)
        
        row.set_child(box)
        return row
    
    def _create_content_area(self):
        """Create right content area for settings"""
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.add_css_class("settings-content")
        self.content_box.set_hexpand(True)
        
        # Content scroll area
        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_scroll.set_vexpand(True)
        
        self.content_stack = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_stack.add_css_class("settings-stack")
        self.content_scroll.set_child(self.content_stack)
        
        self.content_box.append(self.content_scroll)
        self.append(self.content_box)
    
    def _on_category_selected(self, listbox, row):
        """Handle category selection"""
        if row and hasattr(row, 'category_id'):
            self._show_category(row.category_id)
    
    def _show_category(self, category_id: str):
        """Show settings for a category"""
        # Clear current content
        child = self.content_stack.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.content_stack.remove(child)
            child = next_child
        
        # Create settings for category
        if category_id == "appearance":
            self._create_appearance_settings()
        elif category_id == "privacy":
            self._create_privacy_settings()
        elif category_id == "performance":
            self._create_performance_settings()
        elif category_id == "content":
            self._create_content_settings()
        elif category_id == "search":
            self._create_search_settings()
        elif category_id == "workspace":
            self._create_workspace_settings()
        elif category_id == "tabs":
            self._create_tabs_settings()
        elif category_id == "session":
            self._create_session_settings()
        elif category_id == "downloads":
            self._create_downloads_settings()
        elif category_id == "developer":
            self._create_developer_settings()
        elif category_id == "sync":
            self._create_sync_settings()
        elif category_id == "accessibility":
            self._create_accessibility_settings()
    
    def _create_appearance_settings(self):
        """Appearance settings"""
        self._add_section_title("Theme")
        
        self._add_choice("appearance", "theme", "Theme mode",
                        [("dark", "Dark"), ("light", "Light"), ("auto", "Auto")])
        
        self._add_choice("appearance", "color_scheme", "Accent color",
                        [("violet", "Violet"), ("blue", "Blue"), ("green", "Green"),
                         ("orange", "Orange"), ("red", "Red"), ("custom", "Custom")])
        
        self._add_section_title("Layout")
        
        self._add_toggle("appearance", "compact_mode", "Compact mode",
                        "Reduce spacing and padding")
        
        self._add_choice("appearance", "sidebar_position", "Sidebar position",
                        [("left", "Left"), ("right", "Right"), ("floating", "Floating")])
        
        self._add_slider("appearance", "sidebar_width_percent", "Sidebar width", 10, 25, 1, "%")
        
        self._add_choice("appearance", "url_bar_position", "URL bar position",
                        [("top", "Top"), ("bottom", "Bottom"), ("floating", "Floating")])
        
        self._add_section_title("Typography")
        
        self._add_entry("appearance", "font_family", "Font family")
        self._add_slider("appearance", "font_size", "Font size", 9, 24, 1, "px")
        
        self._add_section_title("Visual Effects")
        
        self._add_toggle("appearance", "glassmorphism", "Glassmorphism",
                        "Translucent UI elements")
        self._add_toggle("appearance", "animations", "Animations",
                        "Smooth transitions")
        self._add_toggle("appearance", "blur_background", "Blur background",
                        "Blur behind UI elements")
        self._add_toggle("appearance", "smooth_scrolling", "Smooth scrolling",
                        "Smooth page scrolling")
        
        self._add_section_title("UI Density")
        
        self._add_slider("appearance", "tab_height", "Tab height", 24, 48, 2, "px")
        self._add_slider("appearance", "url_bar_height", "URL bar height", 28, 52, 2, "px")
        
        self._add_toggle("appearance", "show_tab_icons", "Show tab icons",
                        "Display favicon in tabs")
        
        self._add_choice("appearance", "show_tab_close_button", "Tab close button",
                        [("always", "Always"), ("hover", "On hover"), ("never", "Never")])
        
        self._add_section_title("Status Indicators")
        
        self._add_toggle("appearance", "show_loading_bar", "Loading bar",
                        "Show progress bar")
        self._add_toggle("appearance", "show_https_indicator", "HTTPS indicator",
                        "Show security icon")
        self._add_toggle("appearance", "show_tab_count", "Tab count",
                        "Show number of tabs")
    
    def _create_privacy_settings(self):
        """Privacy settings"""
        self._add_section_title("Tracking Protection")
        
        self._add_toggle("privacy", "block_trackers", "Block trackers",
                        "Block known tracking scripts")
        self._add_toggle("privacy", "block_ads", "Block ads",
                        "Built-in ad blocking (or use extension)")
        self._add_toggle("privacy", "block_fingerprinting", "Block fingerprinting",
                        "Prevent browser fingerprinting")
        self._add_toggle("privacy", "block_cryptominers", "Block cryptominers",
                        "Block cryptocurrency miners")
        
        self._add_section_title("Cookies")
        
        self._add_choice("privacy", "cookie_policy", "Cookie policy",
                        [("allow_all", "Allow all"), 
                         ("block_third_party", "Block third-party"),
                         ("block_all", "Block all")])
        
        self._add_toggle("privacy", "clear_cookies_on_exit", "Clear cookies on exit",
                        "Delete cookies when browser closes")
        
        self._add_section_title("History")
        
        self._add_toggle("privacy", "remember_history", "Remember history",
                        "Save browsing history")
        self._add_toggle("privacy", "remember_downloads", "Remember downloads",
                        "Save download history")
        self._add_toggle("privacy", "remember_search_form_history", "Remember searches",
                        "Save search and form history")
        self._add_toggle("privacy", "clear_history_on_exit", "Clear history on exit",
                        "Delete history when browser closes")
        self._add_slider("privacy", "history_expiration_days", "History expiration", 
                        7, 365, 7, " days")
        
        self._add_section_title("HTTPS & DNS")
        
        self._add_toggle("privacy", "https_only_mode", "HTTPS-only mode",
                        "Always use HTTPS connections")
        self._add_toggle("privacy", "enable_dns_over_https", "DNS over HTTPS",
                        "Encrypt DNS queries")
        self._add_choice("privacy", "dns_provider", "DNS provider",
                        [("cloudflare", "Cloudflare"), ("quad9", "Quad9"), 
                         ("custom", "Custom")])
        
        self._add_section_title("Permissions")
        
        self._add_toggle("privacy", "ask_for_location", "Ask for location",
                        "Prompt before sharing location")
        self._add_toggle("privacy", "ask_for_camera", "Ask for camera",
                        "Prompt before accessing camera")
        self._add_toggle("privacy", "ask_for_microphone", "Ask for microphone",
                        "Prompt before accessing microphone")
        self._add_toggle("privacy", "ask_for_notifications", "Ask for notifications",
                        "Prompt before sending notifications")
        self._add_toggle("privacy", "ask_for_autoplay", "Ask for autoplay",
                        "Prompt before autoplaying media")
        
        self._add_section_title("Container Tabs (Firefox)")
        
        self._add_toggle("privacy", "enable_containers", "Enable container tabs",
                        "Isolate cookies per container")
    
    def _create_performance_settings(self):
        """Performance settings (Opera GX style)"""
        self._add_section_title("Resource Limiters")
        
        self._add_toggle("performance", "enable_ram_limiter", "Enable RAM limiter",
                        "Limit memory usage")
        self._add_slider("performance", "ram_limit_mb", "RAM limit", 512, 16384, 512, " MB")
        
        self._add_toggle("performance", "enable_cpu_limiter", "Enable CPU limiter",
                        "Limit CPU usage")
        self._add_slider("performance", "cpu_limit_percent", "CPU limit", 10, 100, 5, "%")
        
        self._add_section_title("Tab Management")
        
        self._add_toggle("performance", "auto_unload_tabs", "Auto-unload tabs",
                        "Unload inactive tabs to save memory")
        self._add_slider("performance", "unload_after_minutes", "Unload after", 
                        1, 60, 1, " min")
        self._add_slider("performance", "max_loaded_tabs", "Max loaded tabs", 
                        3, 50, 1, " tabs")
        self._add_toggle("performance", "suspend_background_tabs", "Suspend background tabs",
                        "Reduce CPU usage of inactive tabs")
        
        self._add_section_title("Hardware Acceleration")
        
        self._add_toggle("performance", "gpu_acceleration", "GPU acceleration",
                        "Use GPU for rendering")
        self._add_toggle("performance", "enable_webgl", "Enable WebGL",
                        "3D graphics support")
        self._add_toggle("performance", "enable_webgl2", "Enable WebGL 2",
                        "Advanced 3D graphics")
        
        self._add_section_title("Network")
        
        self._add_toggle("performance", "enable_prefetch", "Prefetch links",
                        "Preload linked pages")
        self._add_toggle("performance", "enable_preconnect", "Preconnect",
                        "Connect to servers early")
        self._add_toggle("performance", "enable_http3", "Enable HTTP/3",
                        "Use QUIC protocol")
        
        self._add_section_title("Cache")
        
        self._add_slider("performance", "cache_size_mb", "Cache size", 
                        128, 2048, 128, " MB")
        self._add_toggle("performance", "clear_cache_on_exit", "Clear cache on exit",
                        "Delete cache when browser closes")
    
    def _create_content_settings(self):
        """Content settings"""
        self._add_section_title("Media")
        
        self._add_choice("content", "autoplay_policy", "Autoplay policy",
                        [("allow", "Allow"), ("user_gesture", "Require interaction"),
                         ("block", "Block")])
        self._add_toggle("content", "enable_drm", "Enable DRM",
                        "Support protected content")
        self._add_toggle("content", "prefer_reduced_motion", "Reduce motion",
                        "Minimize animations")
        
        self._add_section_title("Images")
        
        self._add_toggle("content", "load_images", "Load images",
                        "Display images on pages")
        self._add_toggle("content", "enable_webp", "Enable WebP",
                        "Modern image format")
        self._add_toggle("content", "enable_avif", "Enable AVIF",
                        "Next-gen image format")
        
        self._add_section_title("Scripts")
        
        self._add_toggle("content", "enable_javascript", "Enable JavaScript",
                        "Run JavaScript code")
        self._add_toggle("content", "enable_wasm", "Enable WebAssembly",
                        "Run compiled code")
        
        self._add_section_title("Fonts")
        
        self._add_toggle("content", "allow_custom_fonts", "Allow custom fonts",
                        "Use web fonts")
        self._add_slider("content", "minimum_font_size", "Minimum font size",
                        6, 24, 1, "px")
        
        self._add_section_title("Force Dark Mode (Opera GX)")
        
        self._add_toggle("content", "force_dark_mode", "Force dark mode",
                        "Apply dark theme to all pages")
    
    def _create_search_settings(self):
        """Search settings"""
        self._add_section_title("Default Search Engine")
        
        self._add_choice("search", "default_engine", "Default engine",
                        [("searxng", "SearXNG"), ("g", "Google"), 
                         ("d", "DuckDuckGo"), ("b", "Brave")])
        
        self._add_entry("search", "searxng_url", "SearXNG URL")
        
        self._add_section_title("Search Suggestions")
        
        self._add_toggle("search", "show_search_suggestions", "Show search suggestions",
                        "Suggest searches as you type")
        self._add_toggle("search", "show_history_suggestions", "Show history",
                        "Suggest from history")
        self._add_toggle("search", "show_bookmark_suggestions", "Show bookmarks",
                        "Suggest from bookmarks")
        self._add_slider("search", "max_suggestions", "Max suggestions",
                        3, 15, 1, " items")
        
        self._add_section_title("Behavior")
        
        self._add_toggle("search", "search_on_type", "Search on type",
                        "Search as you type in URL bar")
        self._add_toggle("search", "open_links_in_new_tab", "Open links in new tab",
                        "Middle-click behavior")
        self._add_toggle("search", "focus_search_on_new_tab", "Focus search on new tab",
                        "Automatically focus URL bar")
    
    def _create_workspace_settings(self):
        """Workspace settings (Zen Browser style)"""
        self._add_section_title("Workspaces")
        
        self._add_toggle("workspace", "enable_workspaces", "Enable workspaces",
                        "Organize tabs by context")
        self._add_toggle("workspace", "auto_switch_workspace", "Auto-switch",
                        "Switch workspace based on activity")
        self._add_toggle("workspace", "isolate_cookies_per_workspace", "Isolate cookies",
                        "Separate cookies per workspace")
    
    def _create_tabs_settings(self):
        """Tab settings"""
        self._add_section_title("New Tab")
        
        self._add_choice("tabs", "new_tab_page", "New tab page",
                        [("homepage", "Homepage"), ("blank", "Blank"), 
                         ("custom", "Custom URL")])
        self._add_entry("tabs", "new_tab_custom_url", "Custom URL")
        
        self._add_section_title("Tab Behavior")
        
        self._add_toggle("tabs", "open_new_tab_next_to_current", "Open next to current",
                        "Open new tabs adjacent")
        self._add_toggle("tabs", "switch_to_new_tab", "Switch to new tab",
                        "Activate new tabs immediately")
        self._add_choice("tabs", "close_tab_selects", "After closing tab",
                        [("next", "Select next"), ("previous", "Select previous"),
                         ("last_active", "Select last active")])
        
        self._add_toggle("tabs", "confirm_close_multiple", "Confirm close multiple",
                        "Ask before closing many tabs")
        self._add_slider("tabs", "confirm_close_multiple_threshold", "Confirmation threshold",
                        2, 20, 1, " tabs")
        
        self._add_section_title("Tab Groups (Chrome)")
        
        self._add_toggle("tabs", "enable_tab_groups", "Enable tab groups",
                        "Group related tabs")
        self._add_toggle("tabs", "auto_group_by_domain", "Auto-group by domain",
                        "Group tabs from same website")
        
        self._add_section_title("Pinned Tabs")
        
        self._add_toggle("tabs", "pinned_tabs_show_title", "Show title in pinned tabs",
                        "Display text for pinned tabs")
        
        self._add_section_title("Recently Closed")
        
        self._add_slider("tabs", "remember_closed_tabs", "Remember closed tabs",
                        5, 50, 5, " tabs")
    
    def _create_session_settings(self):
        """Session settings"""
        self._add_section_title("Startup")
        
        self._add_choice("session", "restore_on_startup", "On startup",
                        [("blank", "Blank page"), ("homepage", "Homepage"),
                         ("last_session", "Last session"), ("urls", "Specific URLs")])
        
        self._add_section_title("Session Management")
        
        self._add_toggle("session", "auto_save_session", "Auto-save session",
                        "Automatically save tabs")
        self._add_slider("session", "save_interval_seconds", "Save interval",
                        10, 300, 10, "s")
        self._add_toggle("session", "enable_session_restore", "Enable restore",
                        "Allow session recovery")
        
        self._add_section_title("Crash Recovery")
        
        self._add_toggle("session", "show_restore_prompt", "Show restore prompt",
                        "Ask to restore after crash")
    
    def _create_downloads_settings(self):
        """Download settings"""
        self._add_section_title("Location")
        
        self._add_entry("downloads", "download_dir", "Download directory")
        self._add_toggle("downloads", "ask_download_location", "Ask where to save",
                        "Prompt for location")
        
        self._add_section_title("Behavior")
        
        self._add_toggle("downloads", "auto_open_downloads", "Auto-open",
                        "Open downloads automatically")
        self._add_toggle("downloads", "show_download_notification", "Show notification",
                        "Notify on completion")
        
        self._add_section_title("Safety")
        
        self._add_toggle("downloads", "warn_dangerous_downloads", "Warn on danger",
                        "Alert for risky files")
        self._add_toggle("downloads", "block_dangerous_downloads", "Block dangerous",
                        "Block risky downloads")
    
    def _create_developer_settings(self):
        """Developer settings"""
        self._add_section_title("DevTools")
        
        self._add_toggle("developer", "enable_devtools", "Enable DevTools",
                        "Web developer tools")
        self._add_choice("developer", "devtools_theme", "DevTools theme",
                        [("dark", "Dark"), ("light", "Light")])
        self._add_choice("developer", "devtools_position", "DevTools position",
                        [("bottom", "Bottom"), ("right", "Right"), 
                         ("window", "Separate window")])
        
        self._add_section_title("Debugging")
        
        self._add_toggle("developer", "enable_remote_debugging", "Remote debugging",
                        "Allow external debuggers")
        self._add_slider("developer", "remote_debugging_port", "Debug port",
                        9000, 9999, 1, "")
        
        self._add_section_title("Extensions")
        
        self._add_toggle("developer", "enable_extensions", "Enable extensions",
                        "Support browser extensions")
        self._add_toggle("developer", "enable_userscripts", "Enable userscripts",
                        "Run custom scripts")
        
        self._add_section_title("Experimental")
        
        self._add_toggle("developer", "enable_experimental_features", 
                        "Experimental features", "Enable unstable features")
        self._add_entry("developer", "user_agent", "Custom user agent")
    
    def _create_sync_settings(self):
        """Sync settings (Chrome-style via RyxHub)"""
        self._add_section_title("RyxHub Sync")
        
        self._add_toggle("sync", "enable_sync", "Enable sync",
                        "Sync with RyxHub")
        self._add_entry("sync", "sync_url", "RyxHub URL")
        
        self._add_section_title("What to Sync")
        
        self._add_toggle("sync", "sync_bookmarks", "Bookmarks",
                        "Sync bookmarks")
        self._add_toggle("sync", "sync_history", "History",
                        "Sync browsing history")
        self._add_toggle("sync", "sync_passwords", "Passwords",
                        "Sync saved passwords")
        self._add_toggle("sync", "sync_tabs", "Tabs",
                        "Sync open tabs")
        self._add_toggle("sync", "sync_extensions", "Extensions",
                        "Sync installed extensions")
        self._add_toggle("sync", "sync_settings", "Settings",
                        "Sync browser settings")
    
    def _create_accessibility_settings(self):
        """Accessibility settings"""
        self._add_section_title("Visual")
        
        self._add_toggle("accessibility", "high_contrast", "High contrast",
                        "Increase contrast")
        self._add_toggle("accessibility", "force_colors", "Force colors",
                        "Override page colors")
        
        self._add_section_title("Text")
        
        self._add_toggle("accessibility", "use_system_font_size", "Use system font size",
                        "Follow system preferences")
        self._add_slider("accessibility", "page_zoom", "Page zoom",
                        0.5, 3.0, 0.1, "×")
        
        self._add_section_title("Navigation")
        
        self._add_toggle("accessibility", "caret_browsing", "Caret browsing",
                        "Navigate with text cursor")
        self._add_toggle("accessibility", "spatial_navigation", "Spatial navigation",
                        "Navigate with arrow keys")
        
        self._add_section_title("Screen Reader")
        
        self._add_toggle("accessibility", "screen_reader_mode", "Screen reader mode",
                        "Optimize for screen readers")
    
    # Helper methods for creating UI elements
    
    def _add_section_title(self, title: str):
        """Add a section title"""
        label = Gtk.Label(label=title)
        label.add_css_class("section-title")
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(16)
        label.set_margin_bottom(8)
        label.set_margin_start(16)
        self.content_stack.append(label)
    
    def _add_toggle(self, category: str, key: str, label: str, description: str = ""):
        """Add a toggle switch"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.add_css_class("setting-row")
        row.set_margin_start(16)
        row.set_margin_end(16)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("setting-label")
        label_widget.set_halign(Gtk.Align.START)
        text_box.append(label_widget)
        
        if description:
            desc = Gtk.Label(label=description)
            desc.add_css_class("setting-description")
            desc.set_halign(Gtk.Align.START)
            text_box.append(desc)
        
        text_box.set_hexpand(True)
        row.append(text_box)
        
        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self.settings.get(category, key, False))
        switch.connect("notify::active", lambda s, _: self.settings.set(category, key, s.get_active()))
        row.append(switch)
        
        self.content_stack.append(row)
    
    def _add_choice(self, category: str, key: str, label: str, choices: list):
        """Add a dropdown choice"""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.add_css_class("setting-row")
        row.set_margin_start(16)
        row.set_margin_end(16)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("setting-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_hexpand(True)
        row.append(label_widget)
        
        dropdown = Gtk.DropDown()
        dropdown.set_valign(Gtk.Align.CENTER)
        
        # Create string list model
        string_list = Gtk.StringList()
        current_value = self.settings.get(category, key, choices[0][0])
        current_idx = 0
        
        for i, (value, display) in enumerate(choices):
            string_list.append(display)
            if value == current_value:
                current_idx = i
        
        dropdown.set_model(string_list)
        dropdown.set_selected(current_idx)
        
        def on_selected(dd, _):
            idx = dd.get_selected()
            if idx < len(choices):
                self.settings.set(category, key, choices[idx][0])
        
        dropdown.connect("notify::selected", on_selected)
        row.append(dropdown)
        
        self.content_stack.append(row)
    
    def _add_slider(self, category: str, key: str, label: str, min_val: float, 
                   max_val: float, step: float, suffix: str = ""):
        """Add a slider"""
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.add_css_class("setting-row")
        row.set_margin_start(16)
        row.set_margin_end(16)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("setting-label")
        label_widget.set_halign(Gtk.Align.START)
        label_widget.set_hexpand(True)
        header.append(label_widget)
        
        value_label = Gtk.Label()
        value_label.add_css_class("setting-value")
        header.append(value_label)
        
        row.append(header)
        
        adjustment = Gtk.Adjustment(
            value=self.settings.get(category, key, min_val),
            lower=min_val,
            upper=max_val,
            step_increment=step,
            page_increment=step * 10
        )
        
        scale = Gtk.Scale()
        scale.set_adjustment(adjustment)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        
        def on_value_changed(adj):
            val = adj.get_value()
            if step >= 1:
                val = int(val)
            value_label.set_text(f"{val}{suffix}")
            self.settings.set(category, key, val)
        
        adjustment.connect("value-changed", on_value_changed)
        on_value_changed(adjustment)  # Set initial value
        
        row.append(scale)
        self.content_stack.append(row)
    
    def _add_entry(self, category: str, key: str, label: str):
        """Add a text entry"""
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.add_css_class("setting-row")
        row.set_margin_start(16)
        row.set_margin_end(16)
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        
        label_widget = Gtk.Label(label=label)
        label_widget.add_css_class("setting-label")
        label_widget.set_halign(Gtk.Align.START)
        row.append(label_widget)
        
        entry = Gtk.Entry()
        entry.set_text(str(self.settings.get(category, key, "")))
        entry.connect("changed", lambda e: self.settings.set(category, key, e.get_text()))
        row.append(entry)
        
        self.content_stack.append(row)
    
    def _on_search(self, search_entry):
        """Handle search in settings"""
        # TODO: Implement settings search
        pass
    
    def _export_settings(self):
        """Export settings to file"""
        from pathlib import Path
        export_path = Path.home() / "ryxsurf-settings.json"
        self.settings.export_settings(export_path)
        log.info(f"Settings exported to {export_path}")
    
    def _import_settings(self):
        """Import settings from file"""
        # TODO: File picker dialog
        pass
    
    def _reset_settings(self):
        """Reset all settings"""
        # TODO: Confirmation dialog
        self.settings.reset_all()
        log.info("Settings reset to defaults")
