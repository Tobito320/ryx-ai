#pragma once

#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <vector>
#include <memory>
#include "tab.h"
#include "keyboard_handler.h"
#include "session_manager.h"
#include <glib.h>

/**
 * BrowserWindow is the main GTK4 window containing the browser UI.
 * 
 * Layout: Unified top bar with [Overview][Sessions][Tab Strip][Address Bar][Window Controls]
 * followed by optional sidebar and main content area.
 * 
 * Ownership: BrowserWindow owns Tab objects and KeyboardHandler.
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

    // Tab operations (called by KeyboardHandler)
    void new_tab(const std::string& url = "");
    void close_current_tab();
    void next_tab();
    void previous_tab();
    void jump_to_tab(size_t index);
    void focus_address_bar();
    void next_session();
    void previous_session();
    void toggle_sidebar();

private:
    // Window and main container
    GtkWindow* window_;
    GtkBox* main_box_;
    
    // Unified top bar components
    GtkBox* top_bar_;
    GtkButton* overview_button_;
    GtkBox* tab_strip_;
    GtkEntry* address_bar_;
    GtkBox* window_controls_;
    GtkBox* session_indicator_;
    
    // Content area
    GtkBox* content_box_;
    GtkBox* sidebar_;
    GtkNotebook* notebook_;
    
    bool sidebar_visible_;
    
    std::unique_ptr<SessionManager> session_manager_;
    std::unique_ptr<KeyboardHandler> keyboard_handler_;
    std::unique_ptr<class TabUnloadManager> unload_manager_;
    std::unique_ptr<class PersistenceManager> persistence_manager_;
    std::unique_ptr<class PasswordManager> password_manager_;
    std::unique_ptr<class ThemeManager> theme_manager_;
    guint unload_timer_id_;
    
    // UI creation methods
    void create_window_controls();
    
    // UI update methods
    void update_tab_bar();
    void update_address_bar();
    void update_notebook();
    void update_session_indicator();
    void update_sidebar();
    void refresh_ui();
    
    // Signal handlers
    static void on_address_bar_activated(GtkEntry* entry, gpointer user_data);
    static void on_tab_close_clicked(GtkButton* button, gpointer user_data);
    
    // Tab webview management
    void ensure_tab_webview_loaded(Tab* tab);
    void show_tab(size_t index);
};
