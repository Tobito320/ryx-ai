# RyxSurf Features & Fixes - 2025-12-11

## New Features Added

### 1. DevTools (F12)
- Opens WebKit Inspector for the current tab
- Full debugging: DOM, Network, Console, Performance
- **Lazy loaded** - 0MB until opened

### 2. Password Manager
- Secure storage using system keyring (libsecret)
- SQLite for metadata (domains, usernames)
- **Lazy loaded** - ~3MB when first used
- Location: `~/.config/ryxsurf/passwords.db`

### 3. Form Autofill
- Automatic login form detection
- Fills credentials on page load if available
- Detects form submissions to offer saving
- **Lazy loaded** - runs only when forms detected

### 4. PDF Viewer
- Built-in PDF viewing with pdf.js
- Features: Zoom, navigation, form filling
- Keyboard shortcuts: Arrow keys, +/-
- **Lazy loaded** - ~15MB when first PDF opened
- Intercepts PDF links and downloads

### 5. Settings Page (Ctrl+, or type "settings")
- Full-screen settings tab
- Sections:
  - Search Engine (Google, SearXNG, DuckDuckGo, Brave)
  - Appearance (Dark mode, URL bar auto-hide)
  - Performance (Tab unload timeout, Max loaded tabs)
  - Passwords (Save/autofill toggles, manage saved)
  - Keyboard shortcuts reference
- Saves to: `~/.config/ryxsurf/settings.json`

### 6. Multiple Search Engines
- Google (default)
- SearXNG (private, self-hosted)
- DuckDuckGo
- Brave Search
- Custom SearXNG URL support

## Media Support Fixed

**GStreamer plugins installed:**
```bash
gst-plugins-good gst-plugins-ugly gst-libav
```

This enables:
- YouTube video playback
- HTML5 audio/video
- VP8/VP9/H.264/H.265 codecs

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+L | Focus URL bar |
| Ctrl+T | New tab |
| Ctrl+W | Close tab |
| Ctrl+R / F5 | Reload |
| Ctrl+B | Toggle sidebar |
| Ctrl+Tab | Next tab |
| Ctrl+1-9 | Go to tab N |
| Ctrl+Shift+T | Reopen closed tab |
| Ctrl+, | Open settings |
| F11 | Fullscreen |
| F12 | DevTools |
| Alt+Left | Back |
| Alt+Right | Forward |

## Theme Support

Detects GTK_THEME environment variable:
- **Dracula** - Purple accent (#bd93f9)
- **Catppuccin** - Mauve accent (#cba6f7)
- **Nord** - Cyan accent (#88c0d0)
- **Default** - Purple accent (#7c3aed)

Run with theme:
```bash
GTK_THEME=Dracula python -m ryxsurf.main
```

## Memory Usage

| Feature | Idle | Active |
|---------|------|--------|
| Base browser | ~80MB | - |
| Password manager | 0MB | ~3MB |
| DevTools | 0MB | ~30MB |
| PDF viewer | 0MB | ~15MB |
| Settings page | 0MB | ~2MB |
| **Total (all active)** | - | ~130MB |

Compare to Chrome (~400MB) or Firefox (~300MB).

## Files Created

```
ryxsurf/src/features/
├── __init__.py      # Feature exports
├── passwords.py     # Password manager (libsecret + SQLite)
├── autofill.py      # Form detection and filling
├── pdf.py           # PDF viewer (pdf.js)
└── settings.py      # Settings page HTML + search engines
```

## Log File

All browser events logged to:
`~/.config/ryxsurf/ryxsurf.log`

Log prefixes:
- `[NAV]` - Navigation
- `[LOAD]` - Page load states
- `[POLICY]` - Resource decisions
- `[PDF]` - PDF interception
- `[AUTOFILL]` - Credential filling
- `[DEVTOOLS]` - Inspector
- `[SETTINGS]` - Config changes

