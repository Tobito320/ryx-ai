#pragma once

#include <string>
#include <vector>
#include <memory>
#include <chrono>

class Session;  // Forward declaration

/**
 * Workspace represents a named persistent container for sessions.
 * 
 * Ownership: Workspace owns its Session objects.
 * Workspaces persist across application restarts.
 */
class Workspace {
public:
    Workspace(const std::string& name);
    ~Workspace();

    // Non-copyable, movable
    Workspace(const Workspace&) = delete;
    Workspace& operator=(const Workspace&) = delete;
    Workspace(Workspace&&) = default;
    Workspace& operator=(Workspace&&) = default;

    // Session management
    Session* add_session(const std::string& name);
    void remove_session(size_t index);
    Session* get_session(size_t index);
    size_t get_session_count() const { return sessions_.size(); }
    
    // Active session
    size_t get_active_session_index() const { return active_session_index_; }
    void set_active_session(size_t index);
    Session* get_active_session();

    // Workspace metadata
    std::string get_name() const { return name_; }
    std::chrono::system_clock::time_point get_created_at() const { return created_at_; }
    std::chrono::system_clock::time_point get_updated_at() const { return updated_at_; }
    void mark_updated();

private:
    std::string name_;
    std::vector<std::unique_ptr<Session>> sessions_;
    size_t active_session_index_;
    std::chrono::system_clock::time_point created_at_;
    std::chrono::system_clock::time_point updated_at_;
};
