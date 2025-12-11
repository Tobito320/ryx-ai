#include "workspace.h"
#include "session.h"
#include <algorithm>

Workspace::Workspace(const std::string& name)
    : name_(name)
    , active_session_index_(0)
    , created_at_(std::chrono::system_clock::now())
    , updated_at_(std::chrono::system_clock::now())
{
}

Workspace::~Workspace() = default;

Session* Workspace::add_session(const std::string& name) {
    auto session = std::make_unique<Session>(name);
    Session* session_ptr = session.get();
    sessions_.push_back(std::move(session));
    active_session_index_ = sessions_.size() - 1;
    mark_updated();
    return session_ptr;
}

void Workspace::remove_session(size_t index) {
    if (index >= sessions_.size()) {
        return;
    }
    
    sessions_.erase(sessions_.begin() + index);
    
    // Adjust active session index
    if (sessions_.empty()) {
        active_session_index_ = 0;
    } else if (active_session_index_ >= sessions_.size()) {
        active_session_index_ = sessions_.size() - 1;
    }
    
    mark_updated();
}

Session* Workspace::get_session(size_t index) {
    if (index >= sessions_.size()) {
        return nullptr;
    }
    return sessions_[index].get();
}

void Workspace::set_active_session(size_t index) {
    if (index < sessions_.size()) {
        active_session_index_ = index;
        mark_updated();
    }
}

Session* Workspace::get_active_session() {
    if (sessions_.empty()) {
        return nullptr;
    }
    return sessions_[active_session_index_].get();
}

void Workspace::mark_updated() {
    updated_at_ = std::chrono::system_clock::now();
}
