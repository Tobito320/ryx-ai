#pragma once

#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <vector>
#include <memory>
#include "tab.h"
#include "keyboard_handler.h"

/**
 * BrowserWindow is the main GTK4 window containing the browser UI.
 * 
 * Ownership: BrowserWindow owns Tab objects and KeyboardHandler.
 * The window manages the visual representation of tabs.
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
    void focus_address_bar();

private:
    GtkWindow* window_;
    GtkBox* main_box_;
    GtkBox* tab_bar_;
    GtkEntry* address_bar_;
    GtkNotebook* notebook_;
    
    std::vector<std::unique_ptr<Tab>> tabs_;
    size_t active_tab_index_;
    
    std::unique_ptr<KeyboardHandler> keyboard_handler_;
    
    // UI update methods
    void update_tab_bar();
    void update_address_bar();
    void update_notebook();
    void refresh_ui();
    
    // Signal handlers
    static void on_address_bar_activated(GtkEntry* entry, gpointer user_data);
    static void on_tab_close_clicked(GtkButton* button, gpointer user_data);
    
    // Tab webview management
    void ensure_tab_webview_loaded(Tab* tab);
    void show_tab(size_t index);
};
