#pragma once

#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>

class BrowserWindow;  // Forward declaration

/**
 * KeyboardHandler manages global keyboard shortcuts for the browser.
 * 
 * All shortcuts are handled at the application level for immediate
 * non-blocking response.
 */
class KeyboardHandler {
public:
    KeyboardHandler(BrowserWindow* browser_window);
    ~KeyboardHandler();

    // Setup keyboard shortcuts on a window
    void setup_shortcuts(GtkWindow* window);

private:
    BrowserWindow* browser_window_;
    
    // Shortcut handlers
    static gboolean on_key_pressed(GtkEventControllerKey* controller,
                                   guint keyval,
                                   guint keycode,
                                   GdkModifierType state,
                                   gpointer user_data);
};
