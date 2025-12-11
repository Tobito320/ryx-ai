#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../include/password_manager.h"
#include "../include/crypto.h"
#include <filesystem>

TEST_CASE("PasswordManager initialization", "[password]") {
    PasswordManager pm;
    
    REQUIRE(pm.initialize());
    REQUIRE(pm.is_autofill_enabled());
    
    pm.close();
}

TEST_CASE("PasswordManager save/retrieve", "[password]") {
    PasswordManager pm;
    REQUIRE(pm.initialize("test_master_password"));
    
    REQUIRE(pm.save("example.com", "user1", "password123"));
    REQUIRE(pm.has_credentials("example.com"));
    
    auto creds = pm.get("example.com");
    REQUIRE(creds.size() > 0);
    REQUIRE(creds[0].username == "user1");
    REQUIRE(creds[0].password == "password123");
    
    pm.close();
}

TEST_CASE("PasswordManager get_one", "[password]") {
    PasswordManager pm;
    REQUIRE(pm.initialize());
    
    pm.save("example.com", "user1", "pass1");
    pm.save("example.com", "user2", "pass2");
    
    auto cred = pm.get_one("example.com");
    REQUIRE(cred.has_value());
    REQUIRE(cred->domain == "example.com");
    
    pm.close();
}

TEST_CASE("PasswordManager delete", "[password]") {
    PasswordManager pm;
    REQUIRE(pm.initialize());
    
    pm.save("example.com", "user1", "pass1");
    REQUIRE(pm.has_credentials("example.com"));
    
    REQUIRE(pm.delete_credential("example.com", "user1"));
    REQUIRE_FALSE(pm.has_credentials("example.com"));
    
    pm.close();
}

TEST_CASE("PasswordManager password generator", "[password]") {
    PasswordManager pm;
    
    std::string pwd1 = pm.generate_password(16, true);
    REQUIRE(pwd1.length() == 16);
    
    std::string pwd2 = pm.generate_password(20, false);
    REQUIRE(pwd2.length() == 20);
    REQUIRE(pwd1 != pwd2);  // Should be different
    
    // Check contains required character types
    bool has_lower = std::any_of(pwd1.begin(), pwd1.end(), ::islower);
    bool has_upper = std::any_of(pwd1.begin(), pwd1.end(), ::isupper);
    REQUIRE(has_lower);
    REQUIRE(has_upper);
}

TEST_CASE("PasswordManager domain extraction", "[password]") {
    PasswordManager pm;
    
    // Test domain extraction (indirectly through autofill)
    REQUIRE(pm.should_autofill("https://example.com/page") == false);
    
    pm.save("example.com", "user", "pass");
    REQUIRE(pm.should_autofill("https://example.com/page") == true);
    
    pm.close();
}
