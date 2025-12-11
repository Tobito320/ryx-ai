#include "snapshot_manager.h"
#include "tab.h"
#include <webkit/webkit.h>
#include <gtk/gtk.h>
#include <cairo/cairo.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <cstdlib>

SnapshotManager::SnapshotManager()
    : snapshots_enabled_(std::getenv("RYXSURF_ENABLE_SNAPSHOTS") != nullptr)
{
    // Use XDG data directory
    const char* xdg_data = std::getenv("XDG_DATA_HOME");
    if (xdg_data) {
        snapshot_dir_ = std::filesystem::path(xdg_data) / "ryxsurf" / "snapshots";
    } else {
        const char* home = std::getenv("HOME");
        if (!home) {
            // Fallback to /tmp if HOME is not set (should not happen in normal usage)
            snapshot_dir_ = std::filesystem::path("/tmp") / "ryxsurf" / "snapshots";
        } else {
            snapshot_dir_ = std::filesystem::path(home) / ".local" / "share" / "ryxsurf" / "snapshots";
        }
    }
    
    if (snapshots_enabled_) {
        ensure_snapshot_dir();
    }
}

SnapshotManager::~SnapshotManager() = default;

void SnapshotManager::ensure_snapshot_dir() {
    std::filesystem::create_directories(snapshot_dir_);
}

std::string SnapshotManager::generate_tab_id(Tab* tab) const {
    // Generate ID from URL + timestamp
    std::stringstream ss;
    ss << std::hex << std::hash<std::string>{}(tab->get_url());
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::duration_cast<std::chrono::seconds>(
        now.time_since_epoch()).count();
    ss << "_" << time;
    return ss.str();
}

std::string SnapshotManager::get_snapshot_path(const std::string& tab_id) const {
    return (snapshot_dir_ / (tab_id + ".png")).string();
}

bool SnapshotManager::snapshot_exists(const std::string& snapshot_path) const {
    return std::filesystem::exists(snapshot_path);
}

std::string SnapshotManager::create_snapshot(Tab* tab) {
    if (!snapshots_enabled_) {
        return "";
    }

    if (!tab || !tab->is_loaded()) {
        return "";
    }
    
    WebKitWebView* webview = tab->get_webview();
    if (!webview) {
        return "";
    }
    
    // Generate snapshot ID
    std::string tab_id = generate_tab_id(tab);
    std::string snapshot_path = get_snapshot_path(tab_id);
    
    // Get WebView size
    int width = gtk_widget_get_width(GTK_WIDGET(webview));
    int height = gtk_widget_get_height(GTK_WIDGET(webview));
    
    if (width <= 0 || height <= 0) {
        // Use default size if not yet rendered
        width = 1920;
        height = 1080;
    }
    
    // Limit snapshot size for memory efficiency (max 512px width)
    const int max_width = 512;
    if (width > max_width) {
        height = (height * max_width) / width;
        width = max_width;
    }
    
    // Create Cairo surface
    cairo_surface_t* surface = cairo_image_surface_create(
        CAIRO_FORMAT_ARGB32, width, height);
    
    if (!surface) {
        return "";
    }
    
    cairo_t* cr = cairo_create(surface);
    
    // Render WebView to surface using WebKit snapshot API
    // Note: This is a simplified version. Real implementation would use
    // webkit_web_view_get_snapshot() or similar API
    cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
    cairo_paint(cr);
    
    // For now, save a placeholder. Real implementation would:
    // 1. Use webkit_web_view_get_snapshot() if available
    // 2. Or use GdkTexture/GdkPixbuf from WebView
    // 3. Save as PNG with compression
    
    cairo_destroy(cr);
    
    // Save PNG
    cairo_surface_write_to_png(surface, snapshot_path.c_str());
    cairo_surface_destroy(surface);
    
    // Save minimal HTML state (URL, title)
    std::string html_path = snapshot_path;
    html_path.replace(html_path.length() - 4, 4, ".html");
    
    std::ofstream html_file(html_path);
    if (html_file.is_open()) {
        html_file << "<!DOCTYPE html>\n";
        html_file << "<html><head><title>" << tab->get_title() << "</title></head>\n";
        html_file << "<body><p>Snapshot of: <a href=\"" << tab->get_url() << "\">" 
                  << tab->get_url() << "</a></p></body></html>\n";
        html_file.close();
    }
    
    return snapshot_path;
}

bool SnapshotManager::restore_snapshot(Tab* tab, const std::string& snapshot_path) {
    if (!snapshots_enabled_) {
        return false;
    }

    if (!tab || !snapshot_exists(snapshot_path)) {
        return false;
    }
    
    // For now, just restore the URL from the HTML file
    std::string html_path = snapshot_path;
    html_path.replace(html_path.length() - 4, 4, ".html");
    
    if (std::filesystem::exists(html_path)) {
        // Parse HTML to extract URL (simplified)
        // Real implementation would parse properly
        std::ifstream html_file(html_path);
        std::string line;
        while (std::getline(html_file, line)) {
            size_t href_pos = line.find("href=\"");
            if (href_pos != std::string::npos) {
                size_t url_start = href_pos + 6;
                size_t url_end = line.find("\"", url_start);
                if (url_end != std::string::npos) {
                    std::string url = line.substr(url_start, url_end - url_start);
                    tab->set_url(url);
                    return true;
                }
            }
        }
    }
    
    return false;
}

void SnapshotManager::delete_snapshot(const std::string& snapshot_path) {
    if (!snapshots_enabled_) {
        return;
    }

    if (std::filesystem::exists(snapshot_path)) {
        std::filesystem::remove(snapshot_path);
    }
    
    std::string html_path = snapshot_path;
    html_path.replace(html_path.length() - 4, 4, ".html");
    if (std::filesystem::exists(html_path)) {
        std::filesystem::remove(html_path);
    }
}
