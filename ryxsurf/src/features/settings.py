"""
Settings Page - Full-screen settings tab

Opens as a tab with full configuration UI.
Uses native GTK4 widgets rendered in a WebView-like HTML interface.
"""

# Settings HTML - opens as a tab
SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Settings</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg: #0a0a0c;
            --bg-lighter: #1a1a20;
            --bg-card: #0e0e12;
            --fg: #e0e0e0;
            --fg-dim: #666;
            --accent: #7c3aed;
            --border: #2a2a30;
        }
        
        body {
            background: var(--bg);
            color: var(--fg);
            font-family: 'Inter', system-ui, sans-serif;
            line-height: 1.6;
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 32px;
            color: var(--fg);
        }
        
        h2 {
            font-size: 16px;
            font-weight: 500;
            color: var(--fg-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 32px 0 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        
        .setting-group {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 16px;
        }
        
        .setting-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
        }
        
        .setting-row:last-child {
            border-bottom: none;
        }
        
        .setting-label {
            flex: 1;
        }
        
        .setting-label h3 {
            font-size: 15px;
            font-weight: 500;
            margin-bottom: 2px;
        }
        
        .setting-label p {
            font-size: 13px;
            color: var(--fg-dim);
        }
        
        .setting-control {
            margin-left: 20px;
        }
        
        /* Toggle switch */
        .toggle {
            position: relative;
            width: 48px;
            height: 26px;
            cursor: pointer;
        }
        
        .toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--border);
            border-radius: 13px;
            transition: 0.2s;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background: white;
            border-radius: 50%;
            transition: 0.2s;
        }
        
        .toggle input:checked + .toggle-slider {
            background: var(--accent);
        }
        
        .toggle input:checked + .toggle-slider:before {
            transform: translateX(22px);
        }
        
        /* Select dropdown */
        select {
            background: var(--bg-lighter);
            color: var(--fg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 32px 8px 12px;
            font-size: 14px;
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
        }
        
        select:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        /* Text input */
        input[type="text"], input[type="number"] {
            background: var(--bg-lighter);
            color: var(--fg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            width: 200px;
        }
        
        input[type="text"]:focus, input[type="number"]:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        /* Button */
        button {
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        
        button:hover {
            opacity: 0.9;
        }
        
        button.secondary {
            background: var(--bg-lighter);
            color: var(--fg);
        }
        
        .button-row {
            display: flex;
            gap: 12px;
            margin-top: 32px;
        }
        
        /* Password list */
        .password-list {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .password-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
        }
        
        .password-item:last-child {
            border-bottom: none;
        }
        
        .password-domain {
            font-weight: 500;
        }
        
        .password-user {
            color: var(--fg-dim);
            font-size: 13px;
        }
        
        .delete-btn {
            background: transparent;
            color: #ff4444;
            padding: 4px 8px;
            font-size: 12px;
        }
        
        /* Keyboard shortcuts */
        .shortcut-list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .shortcut-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            background: var(--bg-lighter);
            border-radius: 6px;
        }
        
        .shortcut-key {
            background: var(--border);
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            min-width: 80px;
            text-align: center;
        }
        
        .shortcut-action {
            color: var(--fg-dim);
            font-size: 13px;
        }
    </style>
</head>
<body>
    <h1>⚙️ Settings</h1>
    
    <h2>🔍 Search Engine</h2>
    <div class="setting-group">
        <div class="setting-row">
            <div class="setting-label">
                <h3>Default Search Engine</h3>
                <p>Used when typing search queries in the URL bar</p>
            </div>
            <div class="setting-control">
                <select id="search-engine" onchange="updateSetting('search_engine', this.value)">
                    <option value="google">Google</option>
                    <option value="searxng">SearXNG (Private)</option>
                    <option value="duckduckgo">DuckDuckGo</option>
                    <option value="brave">Brave Search</option>
                </select>
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>SearXNG Instance</h3>
                <p>Custom SearXNG server URL</p>
            </div>
            <div class="setting-control">
                <input type="text" id="searxng-url" value="http://localhost:8888" 
                       onchange="updateSetting('searxng_url', this.value)">
            </div>
        </div>
    </div>
    
    <h2>🎨 Appearance</h2>
    <div class="setting-group">
        <div class="setting-row">
            <div class="setting-label">
                <h3>Dark Mode</h3>
                <p>Use dark theme for browser UI</p>
            </div>
            <div class="setting-control">
                <label class="toggle">
                    <input type="checkbox" id="dark-mode" checked onchange="updateSetting('dark_mode', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>Auto-hide URL Bar</h3>
                <p>Hide URL bar when scrolling down</p>
            </div>
            <div class="setting-control">
                <label class="toggle">
                    <input type="checkbox" id="url-bar-auto-hide" onchange="updateSetting('url_bar_auto_hide', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>
    </div>
    
    <h2>⚡ Performance</h2>
    <div class="setting-group">
        <div class="setting-row">
            <div class="setting-label">
                <h3>GPU Acceleration</h3>
                <p>Use hardware acceleration for rendering</p>
            </div>
            <div class="setting-control">
                <label class="toggle">
                    <input type="checkbox" id="gpu-acceleration" checked onchange="updateSetting('gpu_acceleration', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>Tab Unload Timeout</h3>
                <p>Unload inactive tabs after (seconds)</p>
            </div>
            <div class="setting-control">
                <input type="number" id="tab-unload-timeout" value="120" min="30" max="3600"
                       onchange="updateSetting('tab_unload_timeout_seconds', parseInt(this.value))">
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>Max Loaded Tabs</h3>
                <p>Maximum tabs kept in memory</p>
            </div>
            <div class="setting-control">
                <input type="number" id="max-loaded-tabs" value="8" min="2" max="20"
                       onchange="updateSetting('max_loaded_tabs', parseInt(this.value))">
            </div>
        </div>
    </div>
    
    <h2>🔐 Passwords</h2>
    <div class="setting-group">
        <div class="setting-row">
            <div class="setting-label">
                <h3>Save Passwords</h3>
                <p>Offer to save passwords when logging in</p>
            </div>
            <div class="setting-control">
                <label class="toggle">
                    <input type="checkbox" id="save-passwords" checked onchange="updateSetting('save_passwords', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>Auto-fill Passwords</h3>
                <p>Automatically fill saved credentials</p>
            </div>
            <div class="setting-control">
                <label class="toggle">
                    <input type="checkbox" id="autofill-passwords" checked onchange="updateSetting('autofill_passwords', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>
    </div>
    
    <div class="setting-group">
        <div class="setting-row" style="flex-direction: column; align-items: stretch;">
            <h3 style="margin-bottom: 12px;">Saved Passwords</h3>
            <div class="password-list" id="password-list">
                <!-- Populated by JavaScript -->
            </div>
        </div>
    </div>
    
    <h2>⌨️ Keyboard Shortcuts</h2>
    <div class="shortcut-list">
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+L</span>
            <span class="shortcut-action">Focus URL bar</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+T</span>
            <span class="shortcut-action">New tab</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+W</span>
            <span class="shortcut-action">Close tab</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+Tab</span>
            <span class="shortcut-action">Next tab</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+1-9</span>
            <span class="shortcut-action">Go to tab N</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+R / F5</span>
            <span class="shortcut-action">Reload</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+B</span>
            <span class="shortcut-action">Toggle sidebar</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">F11</span>
            <span class="shortcut-action">Fullscreen</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">F12</span>
            <span class="shortcut-action">DevTools</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Ctrl+Shift+T</span>
            <span class="shortcut-action">Reopen closed tab</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Alt+Left</span>
            <span class="shortcut-action">Back</span>
        </div>
        <div class="shortcut-item">
            <span class="shortcut-key">Alt+Right</span>
            <span class="shortcut-action">Forward</span>
        </div>
    </div>
    
    <h2>📊 About</h2>
    <div class="setting-group">
        <div class="setting-row">
            <div class="setting-label">
                <h3>RyxSurf</h3>
                <p>Fast, minimal, keyboard-driven browser</p>
            </div>
            <div class="setting-control">
                <span style="color: var(--fg-dim)">v0.1.0</span>
            </div>
        </div>
        <div class="setting-row">
            <div class="setting-label">
                <h3>Engine</h3>
                <p>WebKitGTK 6.0 + GTK4</p>
            </div>
        </div>
    </div>
    
    <script>
        // Settings object
        let settings = {};
        
        // Load settings from Python
        function loadSettings(settingsJson) {
            settings = JSON.parse(settingsJson);
            
            // Apply to UI
            document.getElementById('search-engine').value = settings.search_engine || 'google';
            document.getElementById('searxng-url').value = settings.searxng_url || 'http://localhost:8888';
            document.getElementById('dark-mode').checked = settings.dark_mode !== false;
            document.getElementById('url-bar-auto-hide').checked = settings.url_bar_auto_hide || false;
            document.getElementById('gpu-acceleration').checked = settings.gpu_acceleration !== false;
            document.getElementById('tab-unload-timeout').value = settings.tab_unload_timeout_seconds || 120;
            document.getElementById('max-loaded-tabs').value = settings.max_loaded_tabs || 8;
            document.getElementById('save-passwords').checked = settings.save_passwords !== false;
            document.getElementById('autofill-passwords').checked = settings.autofill_passwords !== false;
        }
        
        // Update setting
        function updateSetting(key, value) {
            settings[key] = value;
            // Send to Python
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.settings) {
                window.webkit.messageHandlers.settings.postMessage({
                    action: 'update',
                    key: key,
                    value: value
                });
            }
        }
        
        // Load password list
        function loadPasswords(passwordsJson) {
            const passwords = JSON.parse(passwordsJson);
            const list = document.getElementById('password-list');
            
            if (passwords.length === 0) {
                list.innerHTML = '<p style="color: var(--fg-dim); padding: 12px;">No saved passwords</p>';
                return;
            }
            
            list.innerHTML = passwords.map(p => `
                <div class="password-item">
                    <div>
                        <div class="password-domain">${p.domain}</div>
                        <div class="password-user">${p.username}</div>
                    </div>
                    <button class="delete-btn" onclick="deletePassword('${p.domain}', '${p.username}')">Delete</button>
                </div>
            `).join('');
        }
        
        // Delete password
        function deletePassword(domain, username) {
            if (confirm('Delete password for ' + domain + '?')) {
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.settings) {
                    window.webkit.messageHandlers.settings.postMessage({
                        action: 'delete_password',
                        domain: domain,
                        username: username
                    });
                }
            }
        }
        
        // Expose to Python
        window.loadSettings = loadSettings;
        window.loadPasswords = loadPasswords;
    </script>
</body>
</html>
"""

# Search engine URLs
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "searxng": "{searxng_url}/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "brave": "https://search.brave.com/search?q=",
}

def get_search_url(settings: dict, query: str) -> str:
    """Get search URL for query based on settings"""
    engine = settings.get("search_engine", "google")
    url_template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["google"])
    
    if "{searxng_url}" in url_template:
        searxng_url = settings.get("searxng_url", "http://localhost:8888")
        url_template = url_template.replace("{searxng_url}", searxng_url)
    
    from urllib.parse import quote_plus
    return url_template + quote_plus(query)
