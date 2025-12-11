#include "tab.h"
#include <webkit/webkit.h>
#include <gtk/gtk.h>

Tab::Tab(const std::string& url)
    : url_(url)
    , title_("New Tab")
    , webview_(nullptr)
    , container_(nullptr)
    , last_active_(std::chrono::steady_clock::now())
    , is_unloaded_(false)
{
}

Tab::~Tab() {
    destroy_webview();
}

WebKitWebView* Tab::get_webview() {
    if (!webview_ && !is_unloaded_) {
        create_webview();
    }
    return webview_;
}

GtkWidget* Tab::get_container() {
    if (!container_ && !is_unloaded_) {
        create_webview();
    }
    return container_;
}

void Tab::create_webview() {
    if (webview_) {
        return;
    }
    
    // Create WebKit settings for minimal resource usage
    WebKitSettings* settings = webkit_settings_new();
    webkit_settings_set_enable_plugins(settings, FALSE);
    webkit_settings_set_enable_java(settings, FALSE);
    webkit_settings_set_enable_media_stream(settings, FALSE);
    webkit_settings_set_enable_mediasource(settings, FALSE);
    webkit_settings_set_hardware_acceleration_policy(
        settings, WEBKIT_HARDWARE_ACCELERATION_POLICY_ALWAYS);
    
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
    is_unloaded_ = false;
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

void Tab::unload() {
    if (is_unloaded_ || !webview_) {
        return;
    }
    
    // Save URL before unloading
    char* uri = webkit_web_view_get_uri(webview_);
    if (uri) {
        url_ = uri;
        g_free(uri);
    }
    
    destroy_webview();
    is_unloaded_ = true;
}

void Tab::restore() {
    if (!is_unloaded_) {
        return;
    }
    
    create_webview();
    if (!url_.empty() && url_ != "about:blank") {
        WebKitWebView* webview = get_webview();
        if (webview) {
            webkit_web_view_load_uri(webview, url_.c_str());
        }
    }
    is_unloaded_ = false;
}

void Tab::mark_active() {
    last_active_ = std::chrono::steady_clock::now();
}
