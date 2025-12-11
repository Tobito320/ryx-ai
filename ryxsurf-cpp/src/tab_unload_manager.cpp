#include "tab_unload_manager.h"
#include "session.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>

TabUnloadManager::TabUnloadManager()
    : unload_timeout_seconds_(120)  // 2 minutes default for aggressive reclaim
    , max_loaded_tabs_(3)
    , snapshot_manager_(std::make_unique<SnapshotManager>())
{
    if (const char* env_timeout = std::getenv("RYXSURF_UNLOAD_TIMEOUT")) {
        int v = std::atoi(env_timeout);
        if (v > 0) {
            unload_timeout_seconds_ = v;
        }
    }
    if (const char* env_max = std::getenv("RYXSURF_MAX_LOADED_TABS")) {
        int v = std::atoi(env_max);
        if (v > 0) {
            max_loaded_tabs_ = v;
        }
    }
}

TabUnloadManager::~TabUnloadManager() = default;

int TabUnloadManager::count_loaded_tabs(Session* session) const {
    if (!session) {
        return 0;
    }
    
    int count = 0;
    for (size_t i = 0; i < session->get_tab_count(); ++i) {
        Tab* tab = session->get_tab(i);
        if (tab && tab->is_loaded() && !tab->is_unloaded()) {
            count++;
        }
    }
    return count;
}

bool TabUnloadManager::should_unload_tab(Tab* tab, size_t tab_index, size_t active_index) const {
    if (!tab || tab_index == active_index) {
        return false;  // Don't unload active tab
    }
    
    if (tab->is_unloaded() || !tab->is_loaded()) {
        return false;  // Already unloaded or not loaded
    }
    
    // Check inactivity timeout
    auto now = std::chrono::steady_clock::now();
    auto last_active = tab->get_last_active();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_active).count();
    
    return elapsed >= unload_timeout_seconds_;
}

void TabUnloadManager::unload_tab(Tab* tab) {
    if (!tab || !tab->is_loaded() || tab->is_unloaded()) {
        return;
    }
    
    // Create snapshot before unloading
    std::string snapshot_path = snapshot_manager_->create_snapshot(tab);
    
    // Unload the tab
    tab->unload();
}

void TabUnloadManager::check_and_unload(Session* session, size_t active_tab_index) {
    if (!session) {
        return;
    }
    
    int loaded_count = count_loaded_tabs(session);
    
    // If we have too many loaded tabs, unload inactive ones
    if (loaded_count > max_loaded_tabs_) {
        // Collect tabs to unload (sorted by last active, oldest first)
        std::vector<std::pair<size_t, Tab*>> candidates;
        
        for (size_t i = 0; i < session->get_tab_count(); ++i) {
            Tab* tab = session->get_tab(i);
            if (tab && should_unload_tab(tab, i, active_tab_index)) {
                candidates.push_back({i, tab});
            }
        }
        
        // Sort by last active (oldest first)
        std::sort(candidates.begin(), candidates.end(),
                  [](const auto& a, const auto& b) {
                      return a.second->get_last_active() < b.second->get_last_active();
                  });
        
        // Unload excess tabs
        int to_unload = loaded_count - max_loaded_tabs_;
        for (int i = 0; i < to_unload && i < static_cast<int>(candidates.size()); ++i) {
            unload_tab(candidates[i].second);
        }
    } else {
        // Check for tabs exceeding timeout
        for (size_t i = 0; i < session->get_tab_count(); ++i) {
            Tab* tab = session->get_tab(i);
            if (tab && should_unload_tab(tab, i, active_tab_index)) {
                unload_tab(tab);
            }
        }
    }
}

void TabUnloadManager::unload_all_except_active(Session* session, size_t active_tab_index) {
    if (!session) {
        return;
    }
    
    for (size_t i = 0; i < session->get_tab_count(); ++i) {
        if (i != active_tab_index) {
            Tab* tab = session->get_tab(i);
            if (tab && tab->is_loaded() && !tab->is_unloaded()) {
                unload_tab(tab);
            }
        }
    }
}
