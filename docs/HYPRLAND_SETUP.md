# Hyprland Integration for Ryx AI

This guide explains how to set up the Ryx AI modal launcher with Hyprland.

## Prerequisites

- Hyprland window manager
- Wofi or Rofi launcher
- notify-send or dunstify for notifications
- jq for JSON parsing

## Installation

### 1. Install the Modal Script

```bash
# Copy script to system bin
sudo cp scripts/ryx-modal /usr/local/bin/ryx-modal
sudo chmod +x /usr/local/bin/ryx-modal
```

### 2. Install Dependencies

```bash
# Arch Linux
sudo pacman -S wofi jq libnotify

# or with Rofi
sudo pacman -S rofi jq libnotify
```

### 3. Configure Hyprland Keybind

Add to your `~/.config/hypr/hyprland.conf`:

```conf
# Ryx AI Modal Launcher
bind = SUPER SHIFT, R, exec, ryx-modal
```

### 4. (Optional) Custom Wofi Theme

Create `~/.config/ryx/wofi.css`:

```css
/* Dracula theme for Ryx AI Wofi */
window {
    background-color: #282a36;
    border: 2px solid #bd93f9;
    border-radius: 8px;
}

#input {
    background-color: #44475a;
    color: #f8f8f2;
    border: none;
    border-radius: 4px;
    margin: 8px;
    padding: 8px 12px;
    font-family: "JetBrains Mono", monospace;
}

#inner-box {
    margin: 0 8px 8px 8px;
}

#entry {
    padding: 8px 12px;
    border-radius: 4px;
}

#entry:selected {
    background-color: #44475a;
    color: #50fa7b;
}

#text {
    color: #f8f8f2;
    font-family: "JetBrains Mono", monospace;
}

#text:selected {
    color: #50fa7b;
}
```

## Usage

1. Press `Super+Shift+R` to open the modal
2. Type your query or select from history
3. Press Enter to execute
4. A notification will show the result

## Customization

### Change Keybind

Edit `hyprland.conf` and change the bind:

```conf
# Example: Use Super+Space instead
bind = SUPER, SPACE, exec, ryx-modal
```

### Change History Size

Edit `/usr/local/bin/ryx-modal` and change:

```bash
MAX_HISTORY=50  # Change to desired number
```

## Troubleshooting

### Script not found

```bash
# Check if script is in PATH
which ryx-modal

# If not, add to PATH or use full path in hyprland.conf
bind = SUPER SHIFT, R, exec, /usr/local/bin/ryx-modal
```

### No notifications

```bash
# Test notifications
notify-send "Test" "Hello"

# If not working, install libnotify
sudo pacman -S libnotify
```

### History not showing

```bash
# Check if history file exists
cat ~/.config/ryx/history.json

# Ensure jq is installed
jq --version
```

## Related Files

- `/usr/local/bin/ryx-modal` - Main script
- `~/.config/ryx/wofi.css` - Wofi theme (optional)
- `~/.config/ryx/history.json` - Command history
- `~/.config/hypr/hyprland.conf` - Hyprland keybind
