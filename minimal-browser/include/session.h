#pragma once

#include "tab.h"
#include <vector>
#include <string>
#include <memory>

/**
 * Session represents a workspace subcontext containing multiple tabs.
 * 
 * Ownership: Session owns its Tab objects. Sessions may be empty
 * (showing Overview placeholder) or contain real tabs.
 */
class Session {
public:
    Session(const std::string& name);
    ~Session();

    // Non-copyable, movable
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
    Session(Session&&) = default;
    Session& operator=(Session&&) = default;

    // Tab management
    Tab* add_tab(const std::string& url = "about:blank");
    void remove_tab(size_t index);
    Tab* get_tab(size_t index);
    size_t get_tab_count() const { return tabs_.size(); }
    size_t get_active_tab_index() const { return active_tab_index_; }
    void set_active_tab(size_t index);
    Tab* get_active_tab();

    // Session metadata
    std::string get_name() const { return name_; }
    bool is_empty() const { return tabs_.empty(); }
    bool is_overview() const { return is_overview_; }
    void set_overview(bool overview) { is_overview_ = overview; }

private:
    std::string name_;
    std::vector<std::unique_ptr<Tab>> tabs_;
    size_t active_tab_index_;
    bool is_overview_;
};
