#include "tab.h"
#include <webkit/webkit.h>
#include <gtk/gtk.h>
#include <iostream>

Tab::Tab(const std::string& url)
    : url_(url)
    , title_("New Tab")
    , webview_(nullptr)
    , last_active_(std::chrono::steady_clock::now())
    , container_(nullptr)
{
}

Tab::~Tab() {
    destroy_webview();
}

WebKitWebView* Tab::get_webview() {
    if (!webview_) {
        create_webview();
    }
    return webview_;
}

void Tab::create_webview() {
    if (webview_) {
        return;  // Already created
    }
    
    // Create WebKit settings for minimal resource usage
    WebKitSettings* settings = webkit_settings_new();
    webkit_settings_set_enable_plugins(settings, FALSE);
    webkit_settings_set_enable_java(settings, FALSE);
    webkit_settings_set_enable_media_stream(settings, FALSE);
    webkit_settings_set_enable_mediasource(settings, FALSE);
    
    // Create WebView
    webview_ = WEBKIT_WEB_VIEW(webkit_web_view_new_with_settings(settings));
    g_object_unref(settings);
    
    // Create container
    container_ = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_box_append(GTK_BOX(container_), GTK_WIDGET(webview_));
    
    // Load URL if set
    if (!url_.empty() && url_ != "about:blank") {
        webkit_web_view_load_uri(webview_, url_.c_str());
    }
    
    // Connect title changed signal
    g_signal_connect(webview_, "notify::title",
                     G_CALLBACK(+[](WebKitWebView* view, GParamSpec*, gpointer data) {
                         Tab* tab = static_cast<Tab*>(data);
                         char* title = webkit_web_view_get_title(view);
                         if (title) {
                             tab->set_title(title);
                             g_free(title);
                         }
                     }), this);
    
    mark_active();
}

void Tab::destroy_webview() {
    if (webview_) {
        if (container_) {
            GtkWidget* parent = gtk_widget_get_parent(container_);
            if (parent) {
                gtk_box_remove(GTK_BOX(parent), container_);
            }
            gtk_widget_unparent(container_);
        }
        g_object_unref(webview_);
        webview_ = nullptr;
        container_ = nullptr;
    }
}

GtkWidget* Tab::get_container() {
    if (!webview_) {
        create_webview();
    }
    return container_;
}

void Tab::mark_active() {
    last_active_ = std::chrono::steady_clock::now();
}
