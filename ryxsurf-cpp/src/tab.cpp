#include "tab.h"
#include <webkit/webkit.h>
#include <gtk/gtk.h>

Tab::Tab(const std::string& url)
    : url_(url)
    , title_("New Tab")
    , webview_(nullptr)
    , container_(nullptr)
    , last_active_(std::chrono::steady_clock::now())
    , last_active_system_(std::chrono::system_clock::now())
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
    
    // Configure shared process + low cache model once
    static bool context_configured = false;
    WebKitWebContext* ctx = webkit_web_context_get_default();
    if (!context_configured && ctx) {
#ifdef WEBKIT_PROCESS_MODEL_SHARED_SECONDARY_PROCESS
        webkit_web_context_set_process_model(ctx, WEBKIT_PROCESS_MODEL_SHARED_SECONDARY_PROCESS);
#endif
        webkit_web_context_set_cache_model(ctx, WEBKIT_CACHE_MODEL_DOCUMENT_VIEWER);
        context_configured = true;
    }

    // Create WebView and apply settings
    webview_ = WEBKIT_WEB_VIEW(webkit_web_view_new());
    g_object_ref_sink(webview_);
    webkit_web_view_set_settings(webview_, settings);
    g_object_unref(settings);
    
    // Create container and take ownership of widgets (sink floating refs)
    container_ = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    g_object_ref_sink(container_);
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
    if (!webview_ && !container_) {
        return;
    }

    // First detach the webview from its parent (typically container_)
    if (webview_) {
        if (gtk_widget_get_parent(GTK_WIDGET(webview_))) {
            gtk_widget_unparent(GTK_WIDGET(webview_));
        }
    }

    // Then detach and release the container if present
    if (container_) {
        if (gtk_widget_get_parent(container_)) {
            gtk_widget_unparent(container_);
        }
        g_object_unref(container_);
    }

    if (webview_) {
        g_object_unref(webview_);
    }

    webview_ = nullptr;
    container_ = nullptr;
}

void Tab::unload() {
    if (is_unloaded_) {
        return;
    }
    
    // Save URL before unloading
    if (webview_) {
        const char* uri = webkit_web_view_get_uri(webview_);
        if (uri) {
            url_ = uri;
        }
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
    last_active_system_ = std::chrono::system_clock::now();
}

void Tab::set_last_active_system(std::chrono::system_clock::time_point tp) {
    last_active_system_ = tp;
    // Align steady clock to "now" so relative comparisons remain monotonic in runtime
    last_active_ = std::chrono::steady_clock::now();
}
