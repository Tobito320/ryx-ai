#!/bin/bash
# Example script: Open URL in minimal browser
# Future: Will use D-Bus or UNIX socket interface

# For now, this is a placeholder demonstrating the intended API

URL="${1:-https://example.com}"
WORKSPACE="${2:-Main}"
SESSION="${3:-}"

echo "Opening $URL in workspace '$WORKSPACE'"
if [ -n "$SESSION" ]; then
    echo "  Session: $SESSION"
fi

# Future implementation:
# dbus-send --session \
#   --type=method_call \
#   --dest=org.minimal.Browser \
#   /org/minimal/Browser \
#   org.minimal.Browser.OpenURL \
#   string:"$URL" string:"$WORKSPACE" string:"$SESSION"

# Or via UNIX socket:
# echo "{\"action\":\"open_url\",\"url\":\"$URL\",\"workspace\":\"$WORKSPACE\"}" | \
#   nc -U /tmp/minimal-browser.sock

echo "Note: IPC interface not yet implemented. See plan.md for roadmap."
