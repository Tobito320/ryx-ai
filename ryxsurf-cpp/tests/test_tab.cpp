#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../include/tab.h"
#include <chrono>
#include <thread>

TEST_CASE("Tab creation", "[tab]") {
    Tab tab("https://example.com");
    
    REQUIRE(tab.get_url() == "https://example.com");
    REQUIRE(tab.get_title() == "New Tab");
    REQUIRE_FALSE(tab.is_loaded());
    REQUIRE_FALSE(tab.is_unloaded());
}

TEST_CASE("Tab lazy loading", "[tab]") {
    Tab tab("https://example.com");
    
    REQUIRE_FALSE(tab.is_loaded());
    
    // WebView should be created on first access
    // Note: This requires GTK/WebKit initialization, so we test metadata only
    REQUIRE(tab.get_url() == "https://example.com");
}

TEST_CASE("Tab activity tracking", "[tab]") {
    Tab tab;
    
    auto time1 = tab.get_last_active();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    tab.mark_active();
    auto time2 = tab.get_last_active();
    
    REQUIRE(time2 > time1);
}

TEST_CASE("Tab unload/restore", "[tab]") {
    Tab tab("https://example.com");
    
    REQUIRE_FALSE(tab.is_unloaded());
    
    // Unload should mark as unloaded
    tab.unload();
    REQUIRE(tab.is_unloaded());
    
    // URL should be preserved
    REQUIRE(tab.get_url() == "https://example.com");
}
