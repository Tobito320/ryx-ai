"""
RyxSurf Extension Support - Firefox WebExtensions Loader

Basic support for loading Firefox extensions:
- Parse manifest.json
- Inject content scripts
- Handle background scripts (limited)
- Support common APIs (storage, tabs)
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import zipfile
import tempfile
import shutil


@dataclass
class ContentScript:
    """Content script definition from manifest"""
    matches: List[str]
    js: List[str] = field(default_factory=list)
    css: List[str] = field(default_factory=list)
    run_at: str = "document_idle"  # document_start, document_end, document_idle


@dataclass 
class Extension:
    """Loaded extension"""
    id: str
    name: str
    version: str
    description: str
    path: Path
    
    content_scripts: List[ContentScript] = field(default_factory=list)
    background_scripts: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    enabled: bool = True


class ExtensionLoader:
    """
    Loads and manages Firefox extensions.
    
    Limitations:
    - Only content scripts fully supported
    - Background scripts run with limited API
    - No popup/options page support yet
    - Storage API is basic (localStorage-backed)
    """
    
    SUPPORTED_APIS = [
        "storage",
        "tabs",  # Limited: only activeTab
        "notifications",  # Via native notifications
    ]
    
    def __init__(self, extensions_dir: Optional[Path] = None):
        self.extensions_dir = extensions_dir or Path.home() / ".config" / "ryxsurf" / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaded: Dict[str, Extension] = {}
        
    def load_all(self):
        """Load all extensions from extensions directory"""
        for ext_dir in self.extensions_dir.iterdir():
            if ext_dir.is_dir():
                try:
                    ext = self._load_extension(ext_dir)
                    if ext:
                        self.loaded[ext.id] = ext
                except Exception as e:
                    print(f"Failed to load extension {ext_dir.name}: {e}")
                    
    def install_from_xpi(self, xpi_path: Path) -> Optional[Extension]:
        """Install extension from .xpi file"""
        if not xpi_path.exists():
            return None
            
        # Extract to temp dir first
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with zipfile.ZipFile(xpi_path, 'r') as zf:
                zf.extractall(temp_path)
                
            # Read manifest to get ID
            manifest_path = temp_path / "manifest.json"
            if not manifest_path.exists():
                return None
                
            manifest = json.loads(manifest_path.read_text())
            
            # Get extension ID
            ext_id = manifest.get("browser_specific_settings", {}).get("gecko", {}).get("id")
            if not ext_id:
                ext_id = manifest.get("name", "unknown").lower().replace(" ", "-")
                
            # Copy to extensions dir
            ext_dir = self.extensions_dir / ext_id
            if ext_dir.exists():
                shutil.rmtree(ext_dir)
            shutil.copytree(temp_path, ext_dir)
            
            # Load and return
            return self._load_extension(ext_dir)
            
    def _load_extension(self, ext_dir: Path) -> Optional[Extension]:
        """Load extension from directory"""
        manifest_path = ext_dir / "manifest.json"
        if not manifest_path.exists():
            return None
            
        manifest = json.loads(manifest_path.read_text())
        
        # Get basic info
        ext_id = manifest.get("browser_specific_settings", {}).get("gecko", {}).get("id")
        if not ext_id:
            ext_id = ext_dir.name
            
        name = manifest.get("name", ext_id)
        version = manifest.get("version", "0.0.0")
        description = manifest.get("description", "")
        
        # Parse content scripts
        content_scripts = []
        for cs in manifest.get("content_scripts", []):
            content_scripts.append(ContentScript(
                matches=cs.get("matches", []),
                js=cs.get("js", []),
                css=cs.get("css", []),
                run_at=cs.get("run_at", "document_idle")
            ))
            
        # Parse background scripts
        background = manifest.get("background", {})
        background_scripts = background.get("scripts", [])
        
        # Parse permissions
        permissions = manifest.get("permissions", [])
        
        return Extension(
            id=ext_id,
            name=name,
            version=version,
            description=description,
            path=ext_dir,
            content_scripts=content_scripts,
            background_scripts=background_scripts,
            permissions=permissions
        )
        
    def get_content_scripts_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Get all content scripts that should run on a URL"""
        import fnmatch
        import re
        
        scripts = []
        
        for ext in self.loaded.values():
            if not ext.enabled:
                continue
                
            for cs in ext.content_scripts:
                for pattern in cs.matches:
                    if self._match_pattern(pattern, url):
                        # Read script contents
                        js_contents = []
                        for js_file in cs.js:
                            js_path = ext.path / js_file
                            if js_path.exists():
                                js_contents.append(js_path.read_text())
                                
                        css_contents = []
                        for css_file in cs.css:
                            css_path = ext.path / css_file
                            if css_path.exists():
                                css_contents.append(css_path.read_text())
                                
                        scripts.append({
                            "extension_id": ext.id,
                            "run_at": cs.run_at,
                            "js": js_contents,
                            "css": css_contents
                        })
                        break
                        
        return scripts
        
    def _match_pattern(self, pattern: str, url: str) -> bool:
        """Match URL against WebExtension match pattern"""
        if pattern == "<all_urls>":
            return True
            
        # Convert match pattern to regex
        # Pattern format: scheme://host/path
        # *:// matches http/https
        # *.example.com matches subdomains
        
        try:
            # Handle *://
            if pattern.startswith("*://"):
                pattern = "(https?)" + pattern[1:]
            elif pattern.startswith("http://"):
                pattern = "http" + pattern[4:]
            elif pattern.startswith("https://"):
                pattern = "https" + pattern[5:]
            else:
                return False
                
            # Escape special chars except *
            pattern = pattern.replace(".", r"\.")
            pattern = pattern.replace("?", r"\?")
            
            # Convert * to .*
            pattern = pattern.replace("*", ".*")
            
            # Match
            return bool(re.match(f"^{pattern}$", url))
        except:
            return False
            
    def get_browser_api_js(self, extension_id: str) -> str:
        """Generate browser API polyfill for extension"""
        return f"""
        // RyxSurf Browser API Polyfill for extension: {extension_id}
        (function() {{
            const extensionId = '{extension_id}';
            
            // Storage API (localStorage-backed)
            const storage = {{
                local: {{
                    get: function(keys) {{
                        return new Promise((resolve) => {{
                            const result = {{}};
                            const keyList = Array.isArray(keys) ? keys : [keys];
                            keyList.forEach(key => {{
                                const value = localStorage.getItem('ext_' + extensionId + '_' + key);
                                if (value) result[key] = JSON.parse(value);
                            }});
                            resolve(result);
                        }});
                    }},
                    set: function(items) {{
                        return new Promise((resolve) => {{
                            Object.entries(items).forEach(([key, value]) => {{
                                localStorage.setItem('ext_' + extensionId + '_' + key, JSON.stringify(value));
                            }});
                            resolve();
                        }});
                    }},
                    remove: function(keys) {{
                        return new Promise((resolve) => {{
                            const keyList = Array.isArray(keys) ? keys : [keys];
                            keyList.forEach(key => {{
                                localStorage.removeItem('ext_' + extensionId + '_' + key);
                            }});
                            resolve();
                        }});
                    }}
                }},
                sync: null  // Not supported, falls back to local
            }};
            storage.sync = storage.local;
            
            // Minimal tabs API
            const tabs = {{
                query: function(queryInfo) {{
                    return new Promise((resolve) => {{
                        // Only return current tab info
                        resolve([{{
                            id: 1,
                            url: window.location.href,
                            title: document.title,
                            active: true
                        }}]);
                    }});
                }},
                sendMessage: function(tabId, message) {{
                    // Not fully supported
                    console.warn('tabs.sendMessage not fully supported in RyxSurf');
                    return Promise.resolve();
                }}
            }};
            
            // Runtime API (minimal)
            const runtime = {{
                getURL: function(path) {{
                    return 'ryxsurf-ext://' + extensionId + '/' + path;
                }},
                sendMessage: function(message) {{
                    console.warn('runtime.sendMessage not fully supported in RyxSurf');
                    return Promise.resolve();
                }},
                onMessage: {{
                    addListener: function(callback) {{
                        // Store for potential future use
                    }}
                }}
            }};
            
            // Expose as browser and chrome (for compatibility)
            window.browser = {{
                storage: storage,
                tabs: tabs,
                runtime: runtime
            }};
            window.chrome = window.browser;
        }})();
        """
        
    def enable(self, extension_id: str):
        """Enable an extension"""
        if extension_id in self.loaded:
            self.loaded[extension_id].enabled = True
            
    def disable(self, extension_id: str):
        """Disable an extension"""
        if extension_id in self.loaded:
            self.loaded[extension_id].enabled = False
            
    def uninstall(self, extension_id: str) -> bool:
        """Uninstall an extension"""
        if extension_id in self.loaded:
            ext = self.loaded.pop(extension_id)
            if ext.path.exists():
                shutil.rmtree(ext.path)
            return True
        return False
        
    def list_extensions(self) -> List[Dict]:
        """List all extensions with their status"""
        return [
            {
                "id": ext.id,
                "name": ext.name,
                "version": ext.version,
                "description": ext.description,
                "enabled": ext.enabled,
                "permissions": ext.permissions
            }
            for ext in self.loaded.values()
        ]
