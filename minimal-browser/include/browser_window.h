#pragma once

#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include "session_manager.h"
#include "keyboard_handler.h"

/**
 * BrowserWindow is the main GTK4 window containing the browser UI.
 * 
 * Ownership: BrowserWindow owns SessionManager and KeyboardHandler.
 * The window manages the visual representation of tabs and sessions.
 */
class BrowserWindow {
public:
    BrowserWindow();
    ~BrowserWindow();

    // Non-copyable, movable
    BrowserWindow(const BrowserWindow&) = delete;
    BrowserWindow& operator=(const BrowserWindow&) = delete;
    BrowserWindow(BrowserWindow&&) = default;
    BrowserWindow& operator=(BrowserWindow&&) = default;

    void show();
    GtkWindow* get_window() { return window_; }

private:
    GtkWindow* window_;
    GtkBox* main_box_;
    GtkBox* tab_bar_;
    GtkEntry* address_bar_;
    GtkBox* session_indicator_;
    GtkNotebook* notebook_;  // Container for tab webviews
    
    std::unique_ptr<SessionManager> session_manager_;
    std::unique_ptr<KeyboardHandler> keyboard_handler_;
    
    // UI update methods
    void update_tab_bar();
    void update_session_indicator();
    void update_address_bar();
    void update_notebook();
    void refresh_ui();  // Refresh all UI elements
    
    // Signal handlers
    static void on_address_bar_activated(GtkEntry* entry, gpointer user_data);
    static void on_tab_close_clicked(GtkButton* button, gpointer user_data);
    
    // Tab webview management
    void ensure_tab_webview_loaded(Tab* tab);
    void show_tab(Tab* tab);
};
