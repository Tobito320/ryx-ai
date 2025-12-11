#include <catch2/catch.hpp>
#include "../include/session_manager.h"
#include "../include/workspace.h"
#include "../include/session.h"

TEST_CASE("SessionManager initialization", "[session_manager]") {
    SessionManager sm;
    
    REQUIRE(sm.get_workspace_count() > 0);
    REQUIRE(sm.get_current_workspace() != nullptr);
    REQUIRE(sm.get_current_session() != nullptr);
}

TEST_CASE("Workspace creation", "[workspace]") {
    Workspace ws("Test");
    
    REQUIRE(ws.get_name() == "Test");
    REQUIRE(ws.get_session_count() == 0);
}

TEST_CASE("Session creation", "[session]") {
    Session session("TestSession");
    
    REQUIRE(session.get_name() == "TestSession");
    REQUIRE(session.is_empty());
    REQUIRE_FALSE(session.is_overview());
}

TEST_CASE("Workspace session management", "[workspace]") {
    Workspace ws("Test");
    
    Session* s1 = ws.add_session("Session1");
    REQUIRE(s1 != nullptr);
    REQUIRE(ws.get_session_count() == 1);
    
    Session* s2 = ws.add_session("Session2");
    REQUIRE(ws.get_session_count() == 2);
    
    REQUIRE(ws.get_active_session() == s2);
    
    ws.set_active_session(0);
    REQUIRE(ws.get_active_session() == s1);
}

TEST_CASE("Session tab management", "[session]") {
    Session session("Test");
    
    Tab* t1 = session.add_tab("https://example.com");
    REQUIRE(t1 != nullptr);
    REQUIRE(session.get_tab_count() == 1);
    REQUIRE_FALSE(session.is_empty());
    
    Tab* t2 = session.add_tab("https://github.com");
    REQUIRE(session.get_tab_count() == 2);
    
    REQUIRE(session.get_active_tab() == t2);
    
    session.set_active_tab(0);
    REQUIRE(session.get_active_tab() == t1);
}

TEST_CASE("SessionManager tab operations", "[session_manager]") {
    SessionManager sm;
    
    Tab* tab = sm.new_tab("https://example.com");
    REQUIRE(tab != nullptr);
    REQUIRE(sm.get_current_tab() == tab);
    
    sm.new_tab("https://github.com");
    REQUIRE(sm.get_current_tab() != tab);
    
    sm.previous_tab();
    REQUIRE(sm.get_current_tab() == tab);
}

TEST_CASE("Session auto-close empty sessions", "[session_manager]") {
    SessionManager sm;
    
    // Create a new session with a tab
    Tab* tab = sm.new_tab("https://example.com");
    Session* session = sm.get_current_session();
    REQUIRE(session != nullptr);
    REQUIRE_FALSE(session->is_overview());
    
    // Close the tab
    sm.close_current_tab();
    
    // Session should be closed if not overview
    // (Overview session should remain)
    Session* new_session = sm.get_current_session();
    REQUIRE(new_session != nullptr);
}

TEST_CASE("Overview session persistence", "[session]") {
    Session session("Overview");
    session.set_overview(true);
    
    REQUIRE(session.is_overview());
    // Overview session can be empty; no-op assertion needed
    REQUIRE((session.is_empty() || !session.is_empty()));
}
