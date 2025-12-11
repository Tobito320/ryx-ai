#include "session.h"
#include <algorithm>

Session::Session(const std::string& name)
    : name_(name)
    , active_tab_index_(0)
    , is_overview_(false)
    , created_at_(std::chrono::system_clock::now())
    , updated_at_(std::chrono::system_clock::now())
{
}

Session::~Session() = default;

Tab* Session::add_tab(const std::string& url) {
    auto tab = std::make_unique<Tab>(url);
    Tab* tab_ptr = tab.get();
    tabs_.push_back(std::move(tab));
    active_tab_index_ = tabs_.size() - 1;
    is_overview_ = false;
    mark_updated();
    return tab_ptr;
}

void Session::remove_tab(size_t index) {
    if (index >= tabs_.size()) {
        return;
    }
    
    tabs_.erase(tabs_.begin() + index);
    
    // Adjust active tab index
    if (tabs_.empty()) {
        active_tab_index_ = 0;
        is_overview_ = true;
    } else if (active_tab_index_ >= tabs_.size()) {
        active_tab_index_ = tabs_.size() - 1;
    }
    
    mark_updated();
}

Tab* Session::get_tab(size_t index) {
    if (index >= tabs_.size()) {
        return nullptr;
    }
    return tabs_[index].get();
}

void Session::set_active_tab(size_t index) {
    if (index < tabs_.size()) {
        active_tab_index_ = index;
        if (tabs_[index]) {
            tabs_[index]->mark_active();
        }
        mark_updated();
    }
}

Tab* Session::get_active_tab() {
    if (tabs_.empty()) {
        return nullptr;
    }
    return tabs_[active_tab_index_].get();
}

void Session::mark_updated() {
    updated_at_ = std::chrono::system_clock::now();
}
