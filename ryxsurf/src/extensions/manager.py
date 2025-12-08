"""
RyxSurf Extension Manager - Browser Integration

Handles injection of extension content scripts into WebViews.
Integrates ExtensionLoader with the Browser class.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

import gi
gi.require_version('WebKit', '6.0')
from gi.repository import WebKit, GLib

from .loader import ExtensionLoader, Extension


class ExtensionManager:
    """
    Manages extension lifecycle and injection into WebViews.
    
    Usage:
        manager = ExtensionManager()
        manager.load_extensions()
        
        # When webview navigates:
        manager.inject_content_scripts(webview, url)
    """
    
    def __init__(self, extensions_dir: Optional[Path] = None):
        self.loader = ExtensionLoader(extensions_dir)
        self.user_content_managers: Dict[int, WebKit.UserContentManager] = {}
        
    def load_extensions(self):
        """Load all extensions from disk"""
        self.loader.load_all()
        print(f"✓ Loaded {len(self.loader.loaded)} extensions")
        
    def install_extension(self, xpi_path: Path) -> Optional[Extension]:
        """Install extension from .xpi file"""
        ext = self.loader.install_from_xpi(xpi_path)
        if ext:
            print(f"✓ Installed extension: {ext.name} v{ext.version}")
        return ext
        
    def setup_webview(self, webview: WebKit.WebView):
        """
        Setup a webview for extension injection.
        Call this when creating a new tab/webview.
        """
        # Get or create user content manager
        webview_id = id(webview)
        
        # Connect to load events for script injection
        webview.connect("load-changed", self._on_load_changed)
        
    def _on_load_changed(self, webview: WebKit.WebView, event: WebKit.LoadEvent):
        """Handle webview load events for content script injection"""
        if event == WebKit.LoadEvent.COMMITTED:
            # Page started loading - inject document_start scripts
            url = webview.get_uri() or ""
            self._inject_scripts(webview, url, "document_start")
            
        elif event == WebKit.LoadEvent.FINISHED:
            # Page finished loading - inject document_end and document_idle scripts
            url = webview.get_uri() or ""
            self._inject_scripts(webview, url, "document_end")
            
            # document_idle - slight delay for full DOM ready
            GLib.timeout_add(100, lambda: self._inject_scripts(webview, url, "document_idle"))
            
    def _inject_scripts(self, webview: WebKit.WebView, url: str, run_at: str):
        """Inject content scripts for the given run_at timing"""
        scripts = self.loader.get_content_scripts_for_url(url)
        
        for script_data in scripts:
            if script_data["run_at"] != run_at:
                continue
                
            ext_id = script_data["extension_id"]
            
            # First inject browser API polyfill
            api_js = self.loader.get_browser_api_js(ext_id)
            webview.evaluate_javascript(api_js, -1, None, None, None, None, None)
            
            # Inject CSS
            for css in script_data["css"]:
                css_escaped = css.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
                inject_css_js = f"""
                (function() {{
                    const style = document.createElement('style');
                    style.textContent = `{css_escaped}`;
                    style.setAttribute('data-ryxsurf-ext', '{ext_id}');
                    (document.head || document.documentElement).appendChild(style);
                }})();
                """
                webview.evaluate_javascript(inject_css_js, -1, None, None, None, None, None)
                
            # Inject JS
            for js in script_data["js"]:
                # Wrap in IIFE to prevent global pollution
                wrapped_js = f"""
                (function() {{
                    try {{
                        {js}
                    }} catch (e) {{
                        console.error('[RyxSurf Extension {ext_id}]', e);
                    }}
                }})();
                """
                webview.evaluate_javascript(wrapped_js, -1, None, None, None, None, None)
                
    def inject_content_scripts(self, webview: WebKit.WebView, url: str):
        """
        Manually inject all content scripts for a URL.
        Use this for initial page load or navigation.
        """
        self._inject_scripts(webview, url, "document_start")
        self._inject_scripts(webview, url, "document_end")
        self._inject_scripts(webview, url, "document_idle")
        
    def get_extension_list(self) -> List[Dict[str, Any]]:
        """Get list of all extensions"""
        return self.loader.list_extensions()
        
    def enable_extension(self, ext_id: str):
        """Enable an extension"""
        self.loader.enable(ext_id)
        
    def disable_extension(self, ext_id: str):
        """Disable an extension"""
        self.loader.disable(ext_id)
        
    def uninstall_extension(self, ext_id: str) -> bool:
        """Uninstall an extension"""
        return self.loader.uninstall(ext_id)


class UserScriptManager:
    """
    Manages user scripts (like Greasemonkey/Tampermonkey).
    Simpler than full extensions - just JS that runs on matched URLs.
    """
    
    def __init__(self, scripts_dir: Optional[Path] = None):
        self.scripts_dir = scripts_dir or Path.home() / ".config" / "ryxsurf" / "userscripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        
        self.scripts: Dict[str, Dict] = {}
        
    def load_scripts(self):
        """Load all user scripts"""
        for script_file in self.scripts_dir.glob("*.user.js"):
            try:
                content = script_file.read_text()
                metadata = self._parse_metadata(content)
                
                self.scripts[script_file.stem] = {
                    "name": metadata.get("name", script_file.stem),
                    "version": metadata.get("version", "1.0"),
                    "match": metadata.get("match", []),
                    "include": metadata.get("include", []),
                    "exclude": metadata.get("exclude", []),
                    "run_at": metadata.get("run-at", "document-idle"),
                    "content": content,
                    "enabled": True
                }
            except Exception as e:
                print(f"Failed to load user script {script_file.name}: {e}")
                
    def _parse_metadata(self, content: str) -> Dict[str, Any]:
        """Parse userscript metadata block"""
        metadata: Dict[str, Any] = {}
        
        import re
        
        # Find metadata block
        match = re.search(r'==UserScript==(.*?)==/UserScript==', content, re.DOTALL)
        if not match:
            return metadata
            
        block = match.group(1)
        
        # Parse @key value pairs
        for line in block.split('\n'):
            line = line.strip()
            if line.startswith('// @'):
                parts = line[4:].split(None, 1)
                if len(parts) == 2:
                    key, value = parts
                    if key in ['match', 'include', 'exclude']:
                        if key not in metadata:
                            metadata[key] = []
                        metadata[key].append(value)
                    else:
                        metadata[key] = value
                        
        return metadata
        
    def get_scripts_for_url(self, url: str) -> List[Dict]:
        """Get user scripts that match URL"""
        import fnmatch
        
        matching = []
        
        for script_id, script in self.scripts.items():
            if not script["enabled"]:
                continue
                
            # Check exclude first
            excluded = False
            for pattern in script.get("exclude", []):
                if fnmatch.fnmatch(url, pattern):
                    excluded = True
                    break
                    
            if excluded:
                continue
                
            # Check match/include
            for pattern in script.get("match", []) + script.get("include", []):
                if pattern == "*" or fnmatch.fnmatch(url, pattern):
                    matching.append(script)
                    break
                    
        return matching
        
    def inject_user_scripts(self, webview: WebKit.WebView, url: str, run_at: str = "document-idle"):
        """Inject matching user scripts into webview"""
        scripts = self.get_scripts_for_url(url)
        
        for script in scripts:
            script_run_at = script.get("run_at", "document-idle").replace("_", "-")
            if script_run_at != run_at:
                continue
                
            wrapped = f"""
            (function() {{
                try {{
                    {script['content']}
                }} catch (e) {{
                    console.error('[RyxSurf UserScript {script["name"]}]', e);
                }}
            }})();
            """
            webview.evaluate_javascript(wrapped, -1, None, None, None, None, None)
