#pragma once

#include "tab.h"
#include "snapshot_manager.h"
#include <vector>
#include <memory>
#include <chrono>
#include <functional>

class Session;  // Forward declaration

/**
 * TabUnloadManager handles automatic tab unloading based on inactivity.
 * 
 * Ownership: TabUnloadManager does not own Tab or Session objects.
 */
class TabUnloadManager {
public:
    TabUnloadManager();
    ~TabUnloadManager();

    // Non-copyable, movable
    TabUnloadManager(const TabUnloadManager&) = delete;
    TabUnloadManager& operator=(const TabUnloadManager&) = delete;
    TabUnloadManager(TabUnloadManager&&) = default;
    TabUnloadManager& operator=(TabUnloadManager&&) = default;

    // Configuration
    void set_unload_timeout_seconds(int seconds) { unload_timeout_seconds_ = seconds; }
    int get_unload_timeout_seconds() const { return unload_timeout_seconds_; }
    void set_max_loaded_tabs(int max) { max_loaded_tabs_ = max; }
    int get_max_loaded_tabs() const { return max_loaded_tabs_; }
    
    // Unload operations
    void check_and_unload(Session* session, size_t active_tab_index);
    void unload_tab(Tab* tab);
    void unload_all_except_active(Session* session, size_t active_tab_index);

private:
    int unload_timeout_seconds_;
    int max_loaded_tabs_;
    std::unique_ptr<SnapshotManager> snapshot_manager_;
    
    bool should_unload_tab(Tab* tab, size_t tab_index, size_t active_index) const;
    int count_loaded_tabs(Session* session) const;
};
