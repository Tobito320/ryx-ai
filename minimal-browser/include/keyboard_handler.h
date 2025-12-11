#pragma once

#include <gtk/gtk.h>
#include "session_manager.h"

/**
 * KeyboardHandler manages global keyboard shortcuts for the browser.
 * 
 * All shortcuts are handled at the application level for immediate
 * non-blocking response.
 */
class BrowserWindow;  // Forward declaration

class KeyboardHandler {
public:
    KeyboardHandler(SessionManager* session_manager, BrowserWindow* browser_window);
    ~KeyboardHandler();

    // Setup keyboard shortcuts on a window
    void setup_shortcuts(GtkWindow* window);

private:
    SessionManager* session_manager_;
    BrowserWindow* browser_window_;
    
    // Shortcut handlers
    static gboolean on_key_pressed(GtkEventControllerKey* controller,
                                   guint keyval,
                                   guint keycode,
                                   GdkModifierType state,
                                   gpointer user_data);
    
    static KeyboardHandler* get_handler(GtkEventControllerKey* controller);
};
