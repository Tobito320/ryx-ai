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
    // Try multiple paths
    std::vector<std::string> paths = {
        "data/theme-gtk4.css",
        "../data/theme-gtk4.css",
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
            window { background: linear-gradient(145deg, #0b0f19 0%, #0f1828 50%, #0b111c 100%); color: #d9e2f2; }
            .tab-bar { background-color: rgba(255, 255, 255, 0.03); border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding: 6px 10px; min-height: 38px; box-shadow: 0 10px 30px -18px rgba(6, 10, 18, 0.55); }
            .tab-button { background-color: transparent; border: 1px solid transparent; border-radius: 10px; padding: 8px 12px; margin: 0 4px; color: #9fb3d8; }
            .tab-button:hover { background-color: #162335; color: #d9e2f2; border-color: rgba(255, 255, 255, 0.08); }
            .tab-button.active-tab { background: linear-gradient(135deg, rgba(75, 194, 255, 0.12), rgba(107, 220, 255, 0.08)); color: #d9e2f2; border-color: rgba(107, 220, 255, 0.5); box-shadow: 0 10px 30px -14px rgba(6, 10, 18, 0.55); }
            .tab-close-button { background-color: transparent; border: none; border-radius: 6px; padding: 2px 6px; margin-left: 6px; opacity: 0.65; }
            .tab-button:hover .tab-close-button { opacity: 1; }
            .tab-close-button:hover { background-color: rgba(255, 255, 255, 0.08); opacity: 1; }
            .address-bar { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 14px; margin: 8px 10px; color: #d9e2f2; font-size: 14px; box-shadow: 0 12px 30px -18px rgba(6, 10, 18, 0.55); }
            .address-bar:focus { border-color: rgba(107, 220, 255, 0.5); background: rgba(107, 220, 255, 0.08); box-shadow: 0 0 0 2px rgba(107, 220, 255, 0.18); }
            .session-indicator { padding: 6px 10px; gap: 6px; background: rgba(255, 255, 255, 0.03); border-bottom: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 8px 24px -18px rgba(6, 10, 18, 0.55); }
            .session-button { background: transparent; border-radius: 8px; padding: 4px 10px; color: #9fb3d8; border: 1px solid transparent; }
            .session-button:hover { background: #162335; color: #d9e2f2; }
            .session-button.active-session { background: rgba(107, 220, 255, 0.12); color: #6bdcff; border-color: rgba(107, 220, 255, 0.5); }
            .sidebar { min-width: 180px; max-width: 260px; background: rgba(255, 255, 255, 0.03); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 10px 8px; }
            .sidebar-tab { background: transparent; border-radius: 8px; padding: 8px 10px; margin-bottom: 4px; text-align: left; color: #9fb3d8; }
            .sidebar-tab:hover { background: #162335; color: #d9e2f2; }
            .sidebar-tab.active-tab { background: linear-gradient(135deg, rgba(75, 194, 255, 0.14), rgba(107, 220, 255, 0.1)); color: #d9e2f2; border: 1px solid rgba(107, 220, 255, 0.5); }
            .sidebar-tab-title { color: inherit; font-size: 13px; }
        )";
        
        gtk_css_provider_load_from_string(css_provider_, inline_css);
    } else {
        gtk_css_provider_load_from_path(css_provider_, css_path.c_str());
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
