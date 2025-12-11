#pragma once

#include <gtk/gtk.h>
#include <string>

/**
 * ThemeManager handles CSS theming and visual customization.
 * 
 * Ownership: ThemeManager does not own GTK widgets.
 */
class ThemeManager {
public:
    enum class Theme {
        Dark,
        Light,
        System
    };
    
    enum class TabLayout {
        Horizontal,
        Vertical
    };
    
    ThemeManager();
    ~ThemeManager();

    // Non-copyable, movable
    ThemeManager(const ThemeManager&) = delete;
    ThemeManager& operator=(const ThemeManager&) = delete;
    ThemeManager(ThemeManager&&) = default;
    ThemeManager& operator=(ThemeManager&&) = default;

    // Theme operations
    void load_theme();
    void set_theme(Theme theme);
    Theme get_theme() const { return current_theme_; }
    
    // Layout operations
    void set_tab_layout(TabLayout layout);
    TabLayout get_tab_layout() const { return tab_layout_; }
    
    // Animation operations
    void set_animations_enabled(bool enabled);
    bool are_animations_enabled() const { return animations_enabled_; }
    
    // Compact mode
    void set_compact_mode(bool enabled);
    bool is_compact_mode() const { return compact_mode_; }
    
    // Apply to window
    void apply_to_window(GtkWindow* window);

private:
    Theme current_theme_;
    TabLayout tab_layout_;
    bool animations_enabled_;
    bool compact_mode_;
    GtkCssProvider* css_provider_;
    
    std::string get_css_path() const;
    void reload_css();
};
