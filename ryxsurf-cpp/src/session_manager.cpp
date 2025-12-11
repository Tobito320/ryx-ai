#include "session_manager.h"
#include <algorithm>

SessionManager::SessionManager()
    : current_workspace_index_(0)
{
    ensure_default_workspace();
}

SessionManager::~SessionManager() = default;

void SessionManager::ensure_default_workspace() {
    if (workspaces_.empty()) {
        auto workspace = std::make_unique<Workspace>("Main");
        workspaces_.push_back(std::move(workspace));
        current_workspace_index_ = 0;
        
        // Create default session "Overview" in the workspace
        Workspace* ws = workspaces_[0].get();
        Session* session = ws->add_session("Overview");
        session->set_overview(true);
    }
}

Workspace* SessionManager::add_workspace(const std::string& name) {
    auto workspace = std::make_unique<Workspace>(name);
    Workspace* workspace_ptr = workspace.get();
    workspaces_.push_back(std::move(workspace));
    return workspace_ptr;
}

Workspace* SessionManager::get_workspace(size_t index) {
    if (index >= workspaces_.size()) {
        return nullptr;
    }
    return workspaces_[index].get();
}

Workspace* SessionManager::get_current_workspace() {
    ensure_default_workspace();
    if (current_workspace_index_ >= workspaces_.size()) {
        current_workspace_index_ = 0;
    }
    return workspaces_[current_workspace_index_].get();
}

Session* SessionManager::get_current_session() {
    Workspace* ws = get_current_workspace();
    if (!ws) {
        return nullptr;
    }
    return ws->get_active_session();
}

Tab* SessionManager::get_current_tab() {
    Session* session = get_current_session();
    if (!session) {
        return nullptr;
    }
    return session->get_active_tab();
}

void SessionManager::switch_workspace(size_t index) {
    if (index < workspaces_.size()) {
        current_workspace_index_ = index;
    }
}

void SessionManager::switch_session(size_t index) {
    Workspace* ws = get_current_workspace();
    if (ws) {
        ws->set_active_session(index);
    }
}

void SessionManager::switch_tab(size_t index) {
    Session* session = get_current_session();
    if (session) {
        session->set_active_tab(index);
    }
}

Tab* SessionManager::new_tab(const std::string& url) {
    Session* session = get_current_session();
    if (!session) {
        ensure_default_workspace();
        Workspace* ws = get_current_workspace();
        session = ws->add_session("Session 1");
    }
    return session->add_tab(url);
}

void SessionManager::close_current_tab() {
    Session* session = get_current_session();
    if (!session) {
        return;
    }
    
    size_t active_index = session->get_active_tab_index();
    session->remove_tab(active_index);
    
    // If session becomes empty and is not overview, close it
    if (session->is_empty() && !session->is_overview()) {
        Workspace* ws = get_current_workspace();
        if (ws) {
            // Find session index
            for (size_t i = 0; i < ws->get_session_count(); ++i) {
                if (ws->get_session(i) == session) {
                    ws->remove_session(i);
                    break;
                }
            }
        }
    }
}

void SessionManager::next_tab() {
    Session* session = get_current_session();
    if (!session || session->get_tab_count() == 0) {
        return;
    }
    
    size_t current = session->get_active_tab_index();
    size_t next = (current + 1) % session->get_tab_count();
    session->set_active_tab(next);
}

void SessionManager::previous_tab() {
    Session* session = get_current_session();
    if (!session || session->get_tab_count() == 0) {
        return;
    }
    
    size_t current = session->get_active_tab_index();
    size_t next = (current == 0) ? session->get_tab_count() - 1 : current - 1;
    session->set_active_tab(next);
}

void SessionManager::next_session() {
    Workspace* ws = get_current_workspace();
    if (!ws || ws->get_session_count() == 0) {
        return;
    }
    
    size_t current = ws->get_active_session_index();
    size_t next = (current + 1) % ws->get_session_count();
    ws->set_active_session(next);
}

void SessionManager::previous_session() {
    Workspace* ws = get_current_workspace();
    if (!ws || ws->get_session_count() == 0) {
        return;
    }
    
    size_t current = ws->get_active_session_index();
    size_t next = (current == 0) ? ws->get_session_count() - 1 : current - 1;
    ws->set_active_session(next);
}

void SessionManager::reset(bool create_default) {
    workspaces_.clear();
    current_workspace_index_ = 0;
    if (create_default) {
        ensure_default_workspace();
    }
}
