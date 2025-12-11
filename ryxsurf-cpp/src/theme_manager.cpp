#include "theme_manager.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>
#include <glib.h>

ThemeManager::ThemeManager()
    : current_theme_(Theme::Dark)
    , tab_layout_(TabLayout::Horizontal)
    , animations_enabled_(true)
    , compact_mode_(false)
    , css_provider_(gtk_css_provider_new())
{
    load_theme();
}

ThemeManager::~ThemeManager() {
    if (css_provider_) {
        g_object_unref(css_provider_);
    }
}

std::string ThemeManager::get_css_path() const {
    // Try to find theme.css in data/ directory relative to executable
    // Or use installed path
    const char* exe_path = g_get_prgname();
    
    // Try multiple paths
    std::vector<std::string> paths = {
        "data/theme.css",
        "../data/theme.css",
        "/usr/share/ryxsurf/theme.css",
        "/usr/local/share/ryxsurf/theme.css",
    };
    
    for (const auto& path : paths) {
        if (std::filesystem::exists(path)) {
            return path;
        }
    }
    
    // Fallback: return default path
    return "data/theme.css";
}

void ThemeManager::load_theme() {
    std::string css_path = get_css_path();
    
    if (!std::filesystem::exists(css_path)) {
        // Use inline CSS as fallback
        const char* inline_css = R"(
            window { background-color: #1e1e2e; color: #cdd6f4; }
            .tab-bar { background-color: #313244; border-bottom: 1px solid rgba(147, 153, 178, 0.2); }
            .tab-button { background-color: transparent; border-radius: 4px; padding: 6px 12px; }
            .tab-button:hover { background-color: #45475a; }
            .tab-button.active-tab { background-color: #45475a; border-bottom: 2px solid #cba6f7; }
            .address-bar { background-color: #313244; border: 1px solid rgba(147, 153, 178, 0.2); border-radius: 6px; padding: 8px 12px; }
            .address-bar:focus { border-color: #cba6f7; box-shadow: 0 0 0 2px rgba(203, 166, 247, 0.2); }
        )";
        
        gtk_css_provider_load_from_data(css_provider_, inline_css, -1);
    } else {
        GError* error = nullptr;
        gtk_css_provider_load_from_path(css_provider_, css_path.c_str(), &error);
        
        if (error) {
            g_error_free(error);
            // Fallback to inline CSS
            load_theme();
        }
    }
    
    // Apply to default display
    GdkDisplay* display = gdk_display_get_default();
    if (display) {
        gtk_style_context_add_provider_for_display(
            display,
            GTK_STYLE_PROVIDER(css_provider_),
            GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    }
}

void ThemeManager::set_theme(Theme theme) {
    current_theme_ = theme;
    reload_css();
}

void ThemeManager::set_tab_layout(TabLayout layout) {
    tab_layout_ = layout;
    reload_css();
}

void ThemeManager::set_animations_enabled(bool enabled) {
    animations_enabled_ = enabled;
    reload_css();
}

void ThemeManager::set_compact_mode(bool enabled) {
    compact_mode_ = enabled;
    reload_css();
}

void ThemeManager::reload_css() {
    // Remove old provider
    GdkDisplay* display = gdk_display_get_default();
    if (display) {
        gtk_style_context_remove_provider_for_display(
            display,
            GTK_STYLE_PROVIDER(css_provider_));
    }
    
    // Reload CSS
    load_theme();
    
    // Apply theme class to root
    if (display) {
        GtkSettings* settings = gtk_settings_get_for_display(display);
        if (current_theme_ == Theme::Light) {
            g_object_set(settings, "gtk-application-prefer-dark-theme", FALSE, nullptr);
        } else if (current_theme_ == Theme::Dark) {
            g_object_set(settings, "gtk-application-prefer-dark-theme", TRUE, nullptr);
        }
    }
}

void ThemeManager::apply_to_window(GtkWindow* window) {
    GtkWidget* widget = GTK_WIDGET(window);
    
    // Apply theme class
    if (current_theme_ == Theme::Light) {
        gtk_widget_add_css_class(widget, "light-theme");
        gtk_widget_remove_css_class(widget, "dark-theme");
    } else {
        gtk_widget_add_css_class(widget, "dark-theme");
        gtk_widget_remove_css_class(widget, "light-theme");
    }
    
    // Apply layout class
    if (tab_layout_ == TabLayout::Vertical) {
        gtk_widget_add_css_class(widget, "vertical-tabs");
        gtk_widget_remove_css_class(widget, "horizontal-tabs");
    } else {
        gtk_widget_add_css_class(widget, "horizontal-tabs");
        gtk_widget_remove_css_class(widget, "vertical-tabs");
    }
    
    // Apply animation class
    if (!animations_enabled_) {
        gtk_widget_add_css_class(widget, "no-animations");
    } else {
        gtk_widget_remove_css_class(widget, "no-animations");
    }
    
    // Apply compact mode
    if (compact_mode_) {
        gtk_widget_add_css_class(widget, "compact");
    } else {
        gtk_widget_remove_css_class(widget, "compact");
    }
}
