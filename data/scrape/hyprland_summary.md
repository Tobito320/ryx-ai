# Hyprland - ArchWiki

Source: https://wiki.archlinux.org/title/Hyprland

## Summary

- **Installation**: Install `hyprland` package. Ensure `Polkit` is installed or enable `seatd.service`. NVIDIA GPU users should refer to upstream documentation for compatibility.
- **Configuration**: Use a single `hyprland.conf` file, located at `/usr/share/hypr/hyprland.conf` or `~/.config/hypr/hyprland.conf`. Supports multiple configuration files. Configuration is automatically reloaded on updates.
- **Key Features**: Dynamic tiling, tabbed windows, custom renderer with animations, rounded corners, and blur effects.
- **Keyboard Settings**: Configure layouts (e.g., US Qwerty, German Colemak) in `hyprland.conf`. Set repeat rate and delay. Use `brightnessctl` for keyboard brightness controls.
- **Commands**: Use `hyprctl reload` to manually reload configuration. Some settings require a session restart. Adjust settings on the fly with `hyprctl`, but they won't be
