# Task 3.5: Hyprland Keybind Modal Script

**Time:** 20 min | **Priority:** MEDIUM | **Agent:** Copilot

## Objective

Create a shell script that integrates Ryx AI with Hyprland via Wofi/Rofi, allowing quick access through a keyboard shortcut (Super+Shift+R).

## Output File(s)

- `scripts/ryx-modal`
- `docs/HYPRLAND_SETUP.md` (installation instructions)

## Requirements

### Shell Script Features

1. Launch Wofi/Rofi in dmenu mode
2. Display recent command history for fuzzy search
3. Execute selected command with Ryx
4. Support new command input
5. Show notification on completion

### Integration Points

- Trigger: `Super+Shift+R`
- History file: `~/.config/ryx/history.json`
- Notification: `notify-send` or `dunstify`

### Wofi/Rofi Configuration

- dmenu mode for input
- Fuzzy matching enabled
- Dark theme matching Dracula
- Recent history displayed

## Code Template

### scripts/ryx-modal

```bash
#!/usr/bin/env bash
#
# ryx-modal - Quick Ryx AI access via Wofi/Rofi
# Integrates with Hyprland for keyboard shortcut activation
#

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

RYX_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ryx"
HISTORY_FILE="$RYX_CONFIG_DIR/history.json"
MAX_HISTORY=50

# Dracula theme colors
BG_COLOR="#282a36"
FG_COLOR="#f8f8f2"
ACCENT_COLOR="#bd93f9"
SELECTED_BG="#44475a"

# Detect launcher (prefer wofi, fallback to rofi)
if command -v wofi &>/dev/null; then
    LAUNCHER="wofi"
elif command -v rofi &>/dev/null; then
    LAUNCHER="rofi"
else
    notify-send "Ryx AI" "Error: Neither wofi nor rofi is installed" -u critical
    exit 1
fi

# =============================================================================
# Functions
# =============================================================================

# Get recent commands from history
get_history() {
    if [[ -f "$HISTORY_FILE" ]]; then
        # Extract user messages from JSON history
        jq -r '.[] | select(.role == "user") | .content' "$HISTORY_FILE" 2>/dev/null | \
            tail -n "$MAX_HISTORY" | \
            tac  # Reverse to show most recent first
    fi
}

# Show launcher and get user input
show_launcher() {
    local prompt="🟣 Ryx: "
    local history
    history=$(get_history)
    
    if [[ "$LAUNCHER" == "wofi" ]]; then
        echo "$history" | wofi \
            --dmenu \
            --prompt "$prompt" \
            --cache-file=/dev/null \
            --insensitive \
            --allow-images \
            --style="$RYX_CONFIG_DIR/wofi.css" 2>/dev/null || \
        echo "$history" | wofi \
            --dmenu \
            --prompt "$prompt" \
            --cache-file=/dev/null \
            --insensitive
    else
        # Rofi with Dracula theme
        echo "$history" | rofi \
            -dmenu \
            -p "$prompt" \
            -i \
            -theme-str "* { background: $BG_COLOR; foreground: $FG_COLOR; }" \
            -theme-str "element selected { background: $SELECTED_BG; }" \
            -theme-str "inputbar { background: $BG_COLOR; foreground: $ACCENT_COLOR; }"
    fi
}

# Execute ryx command
execute_ryx() {
    local query="$1"
    
    if [[ -z "$query" ]]; then
        return 0
    fi
    
    # Show "working" notification
    local notification_id
    notification_id=$(notify-send "Ryx AI" "Processing: $query" --print-id -t 0)
    
    # Execute ryx and capture output
    local output
    local exit_code=0
    output=$(ryx "$query" 2>&1) || exit_code=$?
    
    # Close "working" notification and show result
    if command -v dunstify &>/dev/null; then
        dunstify --close="$notification_id"
    fi
    
    if [[ $exit_code -eq 0 ]]; then
        notify-send "Ryx AI" "✓ Completed\n\n${output:0:200}" -t 5000
    else
        notify-send "Ryx AI" "✗ Error\n\n${output:0:200}" -u critical -t 10000
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Ensure config directory exists
    mkdir -p "$RYX_CONFIG_DIR"
    
    # Show launcher and get input
    local query
    query=$(show_launcher)
    
    # Execute if we got input
    if [[ -n "$query" ]]; then
        execute_ryx "$query"
    fi
}

main "$@"
```

### docs/HYPRLAND_SETUP.md

```markdown
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

## Screenshots

[TODO: Add screenshots of the modal in action]

## Related Files

- `/usr/local/bin/ryx-modal` - Main script
- `~/.config/ryx/wofi.css` - Wofi theme (optional)
- `~/.config/ryx/history.json` - Command history
- `~/.config/hypr/hyprland.conf` - Hyprland keybind
```

## Acceptance Criteria

- [ ] Shell script `ryx-modal` created
- [ ] Script detects and uses Wofi or Rofi
- [ ] History loaded from `~/.config/ryx/history.json`
- [ ] Fuzzy search enabled in launcher
- [ ] Dracula theme colors applied
- [ ] Notification shown on completion
- [ ] Error handling for missing dependencies
- [ ] `HYPRLAND_SETUP.md` documentation created
- [ ] Keybind configuration documented (`Super+Shift+R`)
- [ ] Optional Wofi CSS theme provided
- [ ] Troubleshooting section included
- [ ] Script is executable (`chmod +x`)

## Notes

- Script should fail gracefully if dependencies missing
- History should show most recent commands first
- Wofi preferred over Rofi for Wayland compatibility
- Notification IDs used to replace "working" notification
- jq required for JSON parsing
