# RyxSurf Features

A comprehensive, minimal browser with all features from Chrome, Firefox, Zen Browser, and Opera GX.

## Design Philosophy

- **Symbols over emojis** - Clean, professional icons
- **Subtle over colorful** - Calm color palette
- **Calm over chaotic** - Smooth animations, no distractions
- **Minimal over cluttered** - Every pixel serves a purpose

## Core Features

### 🎨 Beautiful Glassmorphic UI
- Modern glassmorphism design with subtle transparency
- Calm blue-gray color scheme
- Smooth animations (150-400ms)
- Minimal borders and shadows
- Dark theme optimized

### ⚡ Performance Optimized
- **Fast startup** with lazy loading
- **RAM limiter** - Set max memory usage
- **CPU limiter** - Control processor usage
- **GPU limiter** - Prevent screen flicker (max 90%)
- **Tab suspension** - Auto-unload inactive tabs
- **Smart cache** - Optimize disk usage
- **Preloading** - Prefetch likely pages

### 📑 Advanced Tab Management
- **Tab groups** - Organize tabs with colors and icons
- **Workspaces** - Separate contexts (Personal, Work, School, Chill)
- **Tab unloading** - Save memory by hibernating tabs
- **Vertical tabs** - Optional sidebar layout
- **Tab preview** - Hover to preview tab content
- **Middle-click close** - Quick tab closing
- **Tab pinning** - Keep important tabs fixed

### 🪟 Split View & Picture-in-Picture
- **Split screen** - View 2+ tabs side by side
- **Horizontal/Vertical** - Choose your layout
- **Grid view** - 2x2 grid for power users
- **Resizable panes** - Adjust split ratios
- **Picture-in-Picture** - Floating video windows
- **Always on top** - PiP stays visible
- **Opacity control** - See-through windows

### 🔒 Privacy & Security
- **Tracking protection** - Block trackers (strict/standard/off)
- **Ad blocking** - Built-in ad blocker
- **Fingerprint protection** - Prevent fingerprinting
- **HTTPS only** - Force secure connections
- **Do Not Track** - Send DNT header
- **Cookie control** - Block third-party cookies
- **Clear on exit** - Auto-clear history/cache/cookies

### 🔍 Smart Search
- **Multiple engines** - SearXNG, Google, DuckDuckGo, Brave
- **Keyword shortcuts** - `g search` for Google, `w term` for Wikipedia
- **Search suggestions** - Real-time autocomplete
- **URL suggestions** - Smart URL completion
- **Instant search** - Search as you type

### 📥 Download Manager
- **Progress tracking** - See download progress
- **Parallel downloads** - Download multiple files
- **Speed limiter** - Control download speed
- **Auto-open** - Open files when complete
- **Download history** - Track all downloads

### 🔖 Bookmarks & History
- **Smart bookmarks** - Auto-categorize
- **Bookmark sync** - Sync across devices (future)
- **Full history** - Search past pages
- **Quick access** - Dashboard with frequent sites
- **Import/Export** - Compatible with other browsers

### ⌨️ Keyboard-First (Hyprland Style)
```
Navigation:
  Super+j/k     - Scroll down/up
  Super+h/l     - Back/forward
  Super+g       - Focus URL bar
  Super+/       - Search in page
  Super+f       - Hint mode (vimium-style)

Tabs:
  Super+t       - New tab
  Super+w       - Close tab
  Super+1-9     - Jump to tab N
  Super+Tab     - Next tab
  Super+Shift+t - Reopen closed tab

UI:
  Super+b       - Toggle sidebar
  Super+Escape  - Toggle fullscreen
  F12           - Developer tools

AI:
  Super+a       - AI command
  Super+Shift+a - AI summarize
  Super+x       - AI dismiss popup
  Super+r       - Reader mode
```

### 🤖 AI Integration (Ryx-specific)
- **Smart summaries** - Summarize any page
- **Popup dismissal** - Auto-close annoying popups
- **Reader mode** - Extract article text
- **Context menu** - AI options on right-click
- **Sidebar chat** - Ask questions about page
- **Auto-translate** - Translate pages

### 🎮 Gaming Mode (Opera GX Style)
- **GX Control** - Limit RAM/CPU for gaming
- **Network priority** - Prioritize game traffic
- **Hot tabs killer** - Auto-close resource-heavy tabs
- **Force dark mode** - All sites in dark theme
- **Performance overlay** - Monitor resource usage

### 📊 Dashboard Overview
- **Ads blocked** - Total ads blocked
- **Trackers blocked** - Tracking attempts stopped
- **Cookies blocked** - Third-party cookies blocked
- **Bandwidth saved** - Data saved from blocking
- **Pages loaded** - Total page views
- **Time saved** - Time saved from ad blocking
- **Quick access** - Favorite sites
- **Recent sites** - History overview

### 🛠️ Developer Tools
- **Web Inspector** - Full Chrome DevTools
- **Console** - JavaScript console
- **Network monitor** - Track requests
- **Source maps** - Debug original code
- **Remote debugging** - Debug from another device
- **Network throttling** - Simulate slow connections
- **User agent override** - Change browser identity

### 🔧 Advanced Settings

#### General
- Startup page (dashboard/homepage/last session)
- Default search engine
- Downloads location
- Session restore

#### Appearance
- Theme (dark/light/auto)
- Accent color
- Sidebar position (left/right)
- Sidebar width (10-30%)
- Tab style (rounded/squared/minimal)
- Font family and size
- UI density (compact/comfortable/spacious)
- Glassmorphism effects
- Transparency level

#### Privacy
- Tracking protection level
- Ad/tracker/cryptominer blocking
- Cookie policy
- HTTPS-only mode
- Clear data on exit
- DNT header

#### Performance
- Hardware acceleration
- GPU usage limit
- RAM usage limit
- CPU usage limit
- Network bandwidth limit
- Tab suspension timeout
- Max loaded tabs
- Lazy loading
- Smooth scrolling

#### Content
- JavaScript enable/disable
- Images enable/disable
- Popup blocking
- Notifications
- Location access
- Camera/microphone access
- Auto-downloads
- Default zoom level

#### Extensions
- WebExtensions API support
- Firefox extension compatibility
- Auto-update extensions
- Developer mode

#### Sync (Future)
- Sync bookmarks
- Sync history
- Sync passwords
- Sync extensions
- Sync settings

### 🔄 Session Management
- **Auto-save** - Sessions saved automatically
- **Named sessions** - Create custom sessions
- **Workspace sessions** - Per-workspace sessions
- **Import/Export** - Share sessions
- **Tab groups** - Save grouped tabs

### 📱 Web Standards Support
- **WebGL/WebGL2** - 3D graphics
- **WebAssembly** - Near-native performance
- **WebRTC** - Video calls
- **Web Audio** - Audio processing
- **WebExtensions** - Browser extensions
- **Progressive Web Apps** - Install web apps
- **Service Workers** - Offline functionality

## Quick Start

### Rebuild & Install
```bash
cd ryxsurf
./rebuild.sh
```

### Launch
```bash
# Option 1: Direct
python3 main.py

# Option 2: Via launcher
ryxsurf

# Option 3: Via ryx CLI
./ryx surf
```

### First Time Setup
1. Choose your startup page
2. Select search engine
3. Configure keybinds (or use defaults)
4. Set performance limits
5. Enable features you want

## Performance Tips

1. **Enable tab suspension** - Save RAM
2. **Set RAM limit** - Prevent system slowdown
3. **Limit GPU to 90%** - Avoid screen flicker
4. **Enable lazy loading** - Faster startup
5. **Clear cache regularly** - Keep browser snappy
6. **Use tab groups** - Organize and unload tabs
7. **Close unused workspaces** - Free resources

## Troubleshooting

### Browser won't start
```bash
# Check dependencies
python3 -c "import gi; gi.require_version('Gtk', '4.0')"

# Reinstall if needed
pip3 install --user pygobject pycairo
```

### Tabs not loading
- Check internet connection
- Clear cache: Settings → Privacy → Clear cache
- Disable extensions temporarily
- Check GPU acceleration settings

### High RAM usage
- Enable tab suspension
- Set RAM limit in Performance settings
- Reduce max loaded tabs
- Close unused tab groups

### Slow startup
- Enable lazy loading
- Reduce number of startup tabs
- Clear browser cache
- Disable unused extensions

## Comparison

| Feature | RyxSurf | Chrome | Firefox | Zen | Opera GX |
|---------|---------|--------|---------|-----|----------|
| Tab Groups | ✓ | ✓ | ✓ | ✓ | ✓ |
| Workspaces | ✓ | ✗ | ✗ | ✓ | ✗ |
| Split View | ✓ | ✗ | ✗ | ✓ | ✗ |
| RAM Limiter | ✓ | ✗ | ✗ | ✗ | ✓ |
| CPU Limiter | ✓ | ✗ | ✗ | ✗ | ✓ |
| GPU Limiter | ✓ | ✗ | ✗ | ✗ | ✓ |
| AI Integration | ✓ | Paid | ✗ | ✗ | ✗ |
| Privacy-First | ✓ | ✗ | ✓ | ✓ | ✗ |
| Open Source | ✓ | ✗ | ✓ | ✓ | ✗ |
| Keyboard-First | ✓ | ✗ | ✗ | ✓ | ✗ |
| Minimal UI | ✓ | ✗ | ✗ | ✓ | ✗ |

## Roadmap

- [ ] Extension store integration
- [ ] Profile sync across devices
- [ ] Mobile companion app
- [ ] Advanced AI features (auto-fill forms, smart replies)
- [ ] Built-in VPN
- [ ] Advanced theming system
- [ ] Gesture support
- [ ] Voice commands
- [ ] Reading list
- [ ] Note-taking integration

## Credits

Built with:
- **GTK4** - Modern UI toolkit
- **WebKitGTK** - Rendering engine (same as Safari)
- **Python** - Glue language
- **Ollama** - Local AI inference

Inspired by:
- **Zen Browser** - Workspaces and minimal design
- **Opera GX** - Resource limiting
- **Vivaldi** - Power user features
- **Arc Browser** - Modern UI concepts
- **qutebrowser** - Keyboard-first navigation

## License

MIT - See LICENSE file

## Contributing

PRs welcome! Focus areas:
- Performance optimizations
- New keyboard shortcuts
- AI integrations
- Theme improvements
- Bug fixes

Keep the minimal, calm aesthetic in mind.
