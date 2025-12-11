# RyxSurf Installation Summary

## ✅ Installation Complete

RyxSurf has been successfully installed and configured on your system.

---

## 🚀 Launch Methods

### 1. Keyboard Shortcut (Fastest) ⌨️
Press **Alt+D** to launch RyxSurf instantly

> **Note:** The menu launcher (wofi) has been moved to **Alt+Shift+D**

### 2. Command Line 💻
```bash
# Direct command
ryxsurf

# Via ryx wrapper
ryx ryxsurf
ryx surf
ryx browser
```

### 3. Application Menu 🖱️
Search for "RyxSurf" in your application launcher

---

## 🔄 Autostart Configuration

RyxSurf is configured to start automatically when you log in.

**Autostart file:** `~/.config/autostart/ryxsurf.desktop`

To disable autostart:
```bash
rm ~/.config/autostart/ryxsurf.desktop
```

To re-enable:
```bash
cp ~/.local/share/applications/ryxsurf.desktop ~/.config/autostart/
```

---

## 📍 Installation Locations

| Component | Location |
|-----------|----------|
| Binary | `/usr/local/bin/ryxsurf` |
| Desktop Entry | `~/.local/share/applications/ryxsurf.desktop` |
| Autostart Entry | `~/.config/autostart/ryxsurf.desktop` |
| Source Code | `/home/tobi/ryx-ai/ryxsurf-cpp/` |
| Build Directory | `/home/tobi/ryx-ai/ryxsurf-cpp/build/` |

---

## ⌨️ Hyprland Keybinds

| Keybind | Action |
|---------|--------|
| Alt+D | Open menu (wofi) - search for "RyxSurf" |

**Config file:** `~/.config/hypr/hyprland.conf` (unchanged)

---

## 🔧 Updating RyxSurf

When you rebuild RyxSurf, reinstall to system:

```bash
cd /home/tobi/ryx-ai/ryxsurf-cpp
meson compile -C build
sudo cp build/ryxsurf /usr/local/bin/ryxsurf
```

Or use the install script:
```bash
cd /home/tobi/ryx-ai/ryxsurf-cpp
meson install -C build
```

---

## 🧪 Testing Your Installation

1. **Test binary directly:**
   ```bash
   ryxsurf
   ```

2. **Test via ryx command:**
   ```bash
   ryx ryxsurf
   ```

3. **Test keyboard shortcut:**
   - Press **Alt+D**
   - RyxSurf should launch

4. **Test autostart:**
   - Log out and log back in
   - RyxSurf should start automatically

---

## 🎨 Customization

### Change Keybind
Edit `~/.config/hypr/hyprland.conf`:
```conf
bind = $mainMod, D, exec, ryxsurf  # Change D to any key
```
Then reload: `hyprctl reload`

### Disable Autostart
```bash
rm ~/.config/autostart/ryxsurf.desktop
```

### Environment Variables
Set in `~/.config/hypr/hyprland.conf` or `~/.profile`:
```bash
export RYXSURF_UNLOAD_TIMEOUT=300    # 5 minutes instead of 2
export RYXSURF_MAX_LOADED_TABS=5     # 5 tabs instead of 3
export RYXSURF_ENABLE_SNAPSHOTS=1    # Enable snapshots
```

---

## 🐛 Troubleshooting

### RyxSurf doesn't start
1. Check if binary exists:
   ```bash
   ls -lh /usr/local/bin/ryxsurf
   ```

2. Check permissions:
   ```bash
   sudo chmod +x /usr/local/bin/ryxsurf
   ```

3. Test from terminal:
   ```bash
   /usr/local/bin/ryxsurf
   ```

### Alt+D doesn't work
1. Verify keybind:
   ```bash
   grep "bind.*D.*ryxsurf" ~/.config/hypr/hyprland.conf
   ```

2. Reload Hyprland:
   ```bash
   hyprctl reload
   ```

3. If still not working, restart Hyprland (Alt+Shift+M → Log out)

### Autostart not working
1. Check if file exists:
   ```bash
   ls -la ~/.config/autostart/ryxsurf.desktop
   ```

2. Verify file contents:
   ```bash
   cat ~/.config/autostart/ryxsurf.desktop
   ```

3. Check system logs:
   ```bash
   journalctl --user -u ryxsurf.desktop
   ```

---

## 📚 Documentation

- **Main README:** `/home/tobi/ryx-ai/ryxsurf-cpp/README.md`
- **Session Report:** `/home/tobi/ryx-ai/ryxsurf-cpp/SESSION_REPORT.md`
- **Keyboard Shortcuts:** See README.md
- **Environment Variables:** See SESSION_REPORT.md

---

## ✨ Quick Reference

```bash
# Launch RyxSurf
ryxsurf                    # Direct
ryx ryxsurf               # Via wrapper
Alt+D                     # Keyboard shortcut

# Configuration
~/.config/hypr/hyprland.conf           # Keybinds
~/.config/autostart/ryxsurf.desktop    # Autostart
/usr/local/bin/ryxsurf                 # Binary

# Update after rebuild
sudo cp build/ryxsurf /usr/local/bin/ryxsurf

# Disable autostart
rm ~/.config/autostart/ryxsurf.desktop
```

---

**Installation Date:** $(date)  
**Installed By:** Autonomous Agent  
**Status:** Ready to use! Press Alt+D to launch 🚀
