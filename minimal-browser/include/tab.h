#pragma once

#include <webkit/webkit.h>
#include <gtk/gtk.h>
#include <string>
#include <memory>
#include <chrono>

/**
 * Tab represents a single browser tab.
 * 
 * Ownership: Tab owns its WebKitWebView when loaded, but the view
 * is managed by GTK container hierarchy. Tab metadata persists even
 * when webview is unloaded.
 */
class Tab {
public:
    Tab(const std::string& url = "about:blank");
    ~Tab();

    // Non-copyable, movable
    Tab(const Tab&) = delete;
    Tab& operator=(const Tab&) = delete;
    Tab(Tab&&) = default;
    Tab& operator=(Tab&&) = default;

    // WebView management
    WebKitWebView* get_webview();
    GtkWidget* get_container();  // Get GTK container for the webview
    void create_webview();
    void destroy_webview();
    bool is_loaded() const { return webview_ != nullptr; }

    // Metadata
    std::string get_url() const { return url_; }
    std::string get_title() const { return title_; }
    void set_url(const std::string& url) { url_ = url; }
    void set_title(const std::string& title) { title_ = title; }
    
    // Activity tracking
    void mark_active();
    std::chrono::steady_clock::time_point get_last_active() const { return last_active_; }

private:
    std::string url_;
    std::string title_;
    WebKitWebView* webview_;
    std::chrono::steady_clock::time_point last_active_;
    GtkWidget* container_;  // GTK container for the webview
};
