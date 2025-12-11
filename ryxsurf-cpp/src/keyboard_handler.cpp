#include "keyboard_handler.h"
#include "browser_window.h"
#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>

KeyboardHandler::KeyboardHandler(BrowserWindow* browser_window)
    : browser_window_(browser_window)
{
}

KeyboardHandler::~KeyboardHandler() = default;

void KeyboardHandler::setup_shortcuts(GtkWindow* window) {
    GtkEventController* controller = gtk_event_controller_key_new();
    g_signal_connect(controller, "key-pressed",
                     G_CALLBACK(on_key_pressed), this);
    GtkWidget* widget = GTK_WIDGET(window);
    gtk_widget_add_controller(widget, controller);
    g_object_set_data(G_OBJECT(widget), "keyboard-handler", this);
}

gboolean KeyboardHandler::on_key_pressed(GtkEventControllerKey* controller,
                                         guint keyval,
                                         guint keycode,
                                         GdkModifierType state,
                                         gpointer user_data) {
    KeyboardHandler* handler = static_cast<KeyboardHandler*>(user_data);
    BrowserWindow* bw = handler->browser_window_;
    
    // Check for Ctrl modifier
    bool ctrl = (state & GDK_CONTROL_MASK) != 0;
    bool shift = (state & GDK_SHIFT_MASK) != 0;
    
    if (!ctrl) {
        return FALSE;
    }
    
    switch (keyval) {
        case GDK_KEY_t:
            // Ctrl+T: New tab
            bw->new_tab();
            return TRUE;
            
        case GDK_KEY_w:
            // Ctrl+W: Close current tab
            bw->close_current_tab();
            return TRUE;
            
        case GDK_KEY_Up:
            // Ctrl+Up: Previous tab
            bw->previous_tab();
            return TRUE;
            
        case GDK_KEY_Down:
            // Ctrl+Down: Next tab
            bw->next_tab();
            return TRUE;
            
        case GDK_KEY_Left:
            // Ctrl+Left: Previous session (placeholder)
            return TRUE;
            
        case GDK_KEY_Right:
            // Ctrl+Right: Next session (placeholder)
            return TRUE;
            
        case GDK_KEY_Tab:
            // Ctrl+Tab / Ctrl+Shift+Tab: Tab navigation (fallback)
            if (shift) {
                bw->previous_tab();
            } else {
                bw->next_tab();
            }
            return TRUE;
            
        case GDK_KEY_l:
            // Ctrl+L: Focus address bar
            bw->focus_address_bar();
            return TRUE;
            
        case GDK_KEY_s:
            if (shift) {
                // Ctrl+Shift+S: Save session snapshot (placeholder)
                return TRUE;
            }
            break;
    }
    
    return FALSE;
}
