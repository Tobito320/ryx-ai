#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include "../include/persistence_manager.h"
#include "../include/session_manager.h"
#include "../include/crypto.h"
#include <filesystem>
#include <fstream>

TEST_CASE("Crypto key derivation", "[crypto]") {
    Crypto::init();
    
    auto [key1, salt1] = Crypto::derive_key("test_password");
    REQUIRE(key1.size() == Crypto::KEY_SIZE);
    REQUIRE(salt1.size() == Crypto::SALT_SIZE);
    
    // Same password + salt should produce same key
    auto [key2, salt2] = Crypto::derive_key("test_password", salt1);
    REQUIRE(key1 == key2);
}

TEST_CASE("Crypto encrypt/decrypt", "[crypto]") {
    Crypto::init();
    
    auto [key, salt] = Crypto::derive_key("test_password");
    std::string plaintext = "Hello, World!";
    
    std::vector<unsigned char> plaintext_bytes(plaintext.begin(), plaintext.end());
    std::vector<unsigned char> encrypted = Crypto::encrypt(plaintext_bytes, key);
    
    REQUIRE(encrypted.size() > plaintext_bytes.size());
    
    std::vector<unsigned char> decrypted = Crypto::decrypt(encrypted, key);
    std::string decrypted_text(decrypted.begin(), decrypted.end());
    
    REQUIRE(decrypted_text == plaintext);
}

TEST_CASE("PersistenceManager initialization", "[persistence]") {
    SessionManager sm;
    PersistenceManager pm(&sm);
    
    // Create temporary database path
    std::string test_db = "/tmp/test_ryxsurf.db";
    pm.db_path_ = test_db;
    
    REQUIRE(pm.initialize("test_password"));
    REQUIRE(pm.has_master_password());
    
    // Cleanup
    pm.close();
    std::filesystem::remove(test_db);
    std::filesystem::remove(test_db + ".salt");
}

TEST_CASE("PersistenceManager save/load", "[persistence]") {
    SessionManager sm;
    PersistenceManager pm(&sm);
    
    std::string test_db = "/tmp/test_ryxsurf_save.db";
    pm.db_path_ = test_db;
    
    REQUIRE(pm.initialize("test_password"));
    
    // Create test data
    Workspace* ws = sm.add_workspace("TestWorkspace");
    Session* session = ws->add_session("TestSession");
    Tab* tab = session->add_tab("https://example.com");
    tab->set_title("Example");
    
    // Save
    REQUIRE(pm.save_all());
    
    // Create new session manager and load
    SessionManager sm2;
    PersistenceManager pm2(&sm2);
    pm2.db_path_ = test_db;
    REQUIRE(pm2.initialize("test_password"));
    REQUIRE(pm2.load_all());
    
    // Verify loaded data
    REQUIRE(sm2.get_workspace_count() > 0);
    Workspace* loaded_ws = sm2.get_workspace(0);
    REQUIRE(loaded_ws != nullptr);
    REQUIRE(loaded_ws->get_name() == "TestWorkspace");
    
    // Cleanup
    pm.close();
    pm2.close();
    std::filesystem::remove(test_db);
    std::filesystem::remove(test_db + ".salt");
}
