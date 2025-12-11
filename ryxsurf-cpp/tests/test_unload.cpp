#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../include/tab_unload_manager.h"
#include "../include/session.h"
#include <thread>
#include <chrono>

TEST_CASE("TabUnloadManager configuration", "[unload]") {
    TabUnloadManager um;
    
    REQUIRE(um.get_unload_timeout_seconds() == 300);  // 5 minutes default
    REQUIRE(um.get_max_loaded_tabs() == 8);
    
    um.set_unload_timeout_seconds(60);
    REQUIRE(um.get_unload_timeout_seconds() == 60);
    
    um.set_max_loaded_tabs(5);
    REQUIRE(um.get_max_loaded_tabs() == 5);
}

TEST_CASE("Tab unload/restore", "[tab]") {
    Tab tab("https://example.com");
    
    REQUIRE_FALSE(tab.is_unloaded());
    
    tab.unload();
    REQUIRE(tab.is_unloaded());
    REQUIRE_FALSE(tab.is_loaded());
    
    // URL should be preserved
    REQUIRE(tab.get_url() == "https://example.com");
    
    tab.restore();
    // After restore, tab should be ready to load (but not loaded until WebView created)
    REQUIRE_FALSE(tab.is_unloaded());
}

TEST_CASE("SnapshotManager path generation", "[snapshot]") {
    SnapshotManager sm;
    
    std::string path = sm.get_snapshot_path("test123");
    REQUIRE(path.find("test123") != std::string::npos);
    REQUIRE(path.find(".png") != std::string::npos);
}
