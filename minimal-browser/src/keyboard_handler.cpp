#include "keyboard_handler.h"
#include "browser_window.h"
#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>

KeyboardHandler::KeyboardHandler(SessionManager* session_manager, BrowserWindow* browser_window)
    : session_manager_(session_manager)
    , browser_window_(browser_window)
{
}

KeyboardHandler::~KeyboardHandler() = default;

void KeyboardHandler::setup_shortcuts(GtkWindow* window) {
    GtkEventController* controller = gtk_event_controller_key_new();
    g_signal_connect(controller, "key-pressed",
                     G_CALLBACK(on_key_pressed), this);
    GtkWidget* widget = GTK_WIDGET(window);
    gtk_widget_add_controller(widget, controller);
    // Store handler reference for retrieval
    g_object_set_data(G_OBJECT(widget), "keyboard-handler", this);
}

gboolean KeyboardHandler::on_key_pressed(GtkEventControllerKey* controller,
                                         guint keyval,
                                         guint keycode,
                                         GdkModifierType state,
                                         gpointer user_data) {
    KeyboardHandler* handler = static_cast<KeyboardHandler*>(user_data);
    SessionManager* sm = handler->session_manager_;
    
    // Check for Ctrl modifier
    bool ctrl = (state & GDK_CONTROL_MASK) != 0;
    bool shift = (state & GDK_SHIFT_MASK) != 0;
    
    if (!ctrl) {
        return FALSE;  // Not handled
    }
    
    switch (keyval) {
        case GDK_KEY_t:
            // Ctrl+T: New tab
            sm->new_tab();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_w:
            // Ctrl+W: Close current tab
            sm->close_current_tab();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_Up:
            // Ctrl+Up: Previous tab
            sm->previous_tab();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_Down:
            // Ctrl+Down: Next tab
            sm->next_tab();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_Left:
            // Ctrl+Left: Previous session
            sm->previous_session();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_Right:
            // Ctrl+Right: Next session
            sm->next_session();
            if (handler->browser_window_) {
                handler->browser_window_->refresh_ui();
            }
            return TRUE;
            
        case GDK_KEY_Tab:
            // Ctrl+Tab / Ctrl+Shift+Tab: Tab navigation (fallback)
            if (shift) {
                sm->previous_tab();
            } else {
                sm->next_tab();
            }
            return TRUE;
            
        case GDK_KEY_l:
            // Ctrl+L: Focus address bar (handled by window)
            return FALSE;  // Let window handle it
            
        case GDK_KEY_s:
            if (shift) {
                // Ctrl+Shift+S: Save session snapshot (TODO)
                return TRUE;
            }
            break;
    }
    
    return FALSE;
}

KeyboardHandler* KeyboardHandler::get_handler(GtkEventControllerKey* controller) {
    // Retrieve handler from widget data
    GtkWidget* widget = gtk_event_controller_get_widget(GTK_EVENT_CONTROLLER(controller));
    gpointer data = g_object_get_data(G_OBJECT(widget), "keyboard-handler");
    return static_cast<KeyboardHandler*>(data);
}
