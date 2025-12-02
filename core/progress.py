"""
Ryx AI - Progress Indicators

Provides spinners, progress bars, and status updates for long operations.
"""

import sys
import time
import threading
from typing import Optional, Callable
from contextlib import contextmanager

from core.theme import get_theme, ANSI


class Spinner:
    """
    Animated spinner for long operations.
    
    Usage:
        with Spinner("Loading..."):
            do_something_slow()
    
    Or manually:
        spinner = Spinner("Loading...")
        spinner.start()
        do_something_slow()
        spinner.stop()
    """
    
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    INTERVAL = 0.08  # seconds between frames
    
    def __init__(self, message: str = "Working..."):
        self.message = message
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_idx = 0
        self.theme = get_theme()
    
    def _spin(self):
        """Animation loop"""
        while self._running:
            frame = self.FRAMES[self._frame_idx % len(self.FRAMES)]
            color = ANSI.fg_hex(self.theme.colors.info)
            
            # Write spinner + message, then clear to end of line
            sys.stdout.write(f"\r{color}{frame}{ANSI.RESET} {self.message}\033[K")
            sys.stdout.flush()
            
            self._frame_idx += 1
            time.sleep(self.INTERVAL)
    
    def start(self):
        """Start the spinner"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
    
    def stop(self, final_message: Optional[str] = None, success: bool = True):
        """Stop the spinner"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        
        # Clear the line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        
        # Print final message if provided
        if final_message:
            icon = self.theme.icons["success" if success else "error"]
            color_fn = self.theme.success if success else self.theme.error
            print(f"{color_fn(icon)} {final_message}")
    
    def update(self, message: str):
        """Update the spinner message"""
        self.message = message
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


class ProgressBar:
    """
    Simple progress bar for operations with known total.
    
    Usage:
        bar = ProgressBar("Downloading", total=100)
        for i in range(100):
            bar.update(i + 1)
        bar.finish()
    """
    
    def __init__(self, message: str, total: int, width: int = 30):
        self.message = message
        self.total = total
        self.width = width
        self.current = 0
        self.theme = get_theme()
    
    def update(self, current: int):
        """Update progress"""
        self.current = current
        self._render()
    
    def _render(self):
        """Render the progress bar"""
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        empty = self.width - filled
        
        bar = "█" * filled + "░" * empty
        color = ANSI.fg_hex(self.theme.colors.primary)
        
        sys.stdout.write(f"\r{color}{bar}{ANSI.RESET} {percent:>5.1%} {self.message}\033[K")
        sys.stdout.flush()
    
    def finish(self, final_message: Optional[str] = None):
        """Complete the progress bar"""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        
        if final_message:
            icon = self.theme.icons["success"]
            print(f"{self.theme.success(icon)} {final_message}")


class StatusLine:
    """
    Persistent status line at bottom of terminal.
    Updates in place without scrolling.
    """
    
    def __init__(self):
        self.theme = get_theme()
        self._last_message = ""
    
    def update(self, message: str):
        """Update the status line"""
        self._last_message = message
        color = ANSI.fg_hex(self.theme.colors.fg_dim)
        sys.stdout.write(f"\r{color}{message}{ANSI.RESET}\033[K")
        sys.stdout.flush()
    
    def clear(self):
        """Clear the status line"""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


@contextmanager
def spinner(message: str = "Working..."):
    """Context manager for spinner"""
    s = Spinner(message)
    s.start()
    try:
        yield s
    finally:
        s.stop()


def with_spinner(message: str = "Working..."):
    """Decorator for functions that take time"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            with spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Quick test
if __name__ == "__main__":
    print("Testing spinner...")
    with Spinner("Loading model...") as s:
        time.sleep(2)
        s.update("Processing...")
        time.sleep(1)
    print("Done!")
    
    print("\nTesting progress bar...")
    bar = ProgressBar("Downloading", total=50)
    for i in range(50):
        bar.update(i + 1)
        time.sleep(0.05)
    bar.finish("Download complete!")
