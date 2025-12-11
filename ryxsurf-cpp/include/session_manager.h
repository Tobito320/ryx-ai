#pragma once

#include "workspace.h"
#include <vector>
#include <string>
#include <memory>

/**
 * SessionManager manages workspaces and provides high-level session operations.
 * 
 * Ownership: SessionManager owns all Workspace objects. This is the root
 * of the session hierarchy: Workspace -> Session -> Tab.
 */
class SessionManager {
public:
    SessionManager();
    ~SessionManager();

    // Non-copyable, movable
    SessionManager(const SessionManager&) = delete;
    SessionManager& operator=(const SessionManager&) = delete;
    SessionManager(SessionManager&&) = default;
    SessionManager& operator=(SessionManager&&) = default;

    // Workspace management
    Workspace* add_workspace(const std::string& name);
    Workspace* get_workspace(size_t index);
    size_t get_workspace_count() const { return workspaces_.size(); }
    
    // Current workspace/session/tab access
    Workspace* get_current_workspace();
    Session* get_current_session();
    Tab* get_current_tab();
    
    // Navigation
    void switch_workspace(size_t index);
    void switch_session(size_t index);
    void switch_tab(size_t index);
    
    // Tab operations
    Tab* new_tab(const std::string& url = "about:blank");
    void close_current_tab();
    
    // Tab navigation within current session
    void next_tab();
    void previous_tab();
    
    // Session navigation within current workspace
    void next_session();
    void previous_session();

    // State management
    void reset(bool create_default = true);

private:
    std::vector<std::unique_ptr<Workspace>> workspaces_;
    size_t current_workspace_index_;
    
    void ensure_default_workspace();
};
