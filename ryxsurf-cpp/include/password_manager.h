#pragma once

#include "crypto.h"
#include <libsecret/secret.h>
#include <sqlite3.h>
#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <chrono>
#include <webkit/webkit.h>

/**
 * Credential structure for password storage.
 */
struct Credential {
    std::string domain;
    std::string username;
    std::string password;
    std::chrono::system_clock::time_point created;
    std::chrono::system_clock::time_point last_used;
};

/**
 * PasswordManager handles credential storage with dual backend:
 * 1. Primary: libsecret (Secret Service API - GNOME Keyring/KWallet)
 * 2. Fallback: Encrypted SQLite (if libsecret unavailable)
 * 
 * Ownership: PasswordManager owns its database connection.
 */
class PasswordManager {
public:
    PasswordManager();
    ~PasswordManager();

    // Non-copyable, movable
    PasswordManager(const PasswordManager&) = delete;
    PasswordManager& operator=(const PasswordManager&) = delete;
    PasswordManager(PasswordManager&&) = default;
    PasswordManager& operator=(PasswordManager&&) = default;

    // Initialization
    bool initialize(const std::string& master_password = "");
    void close();
    
    // Credential operations
    bool save(const std::string& domain, const std::string& username, const std::string& password);
    std::vector<Credential> get(const std::string& domain);
    std::optional<Credential> get_one(const std::string& domain);
    bool has_credentials(const std::string& domain);
    bool delete_credential(const std::string& domain, const std::string& username);
    void update_last_used(const std::string& domain, const std::string& username);
    
    // Domain operations
    std::vector<std::string> list_domains();
    
    // Autofill
    void autofill(WebKitWebView* webview, const std::string& origin);
    bool should_autofill(const std::string& origin) const;
    void set_autofill_enabled(bool enabled) { autofill_enabled_ = enabled; }
    bool is_autofill_enabled() const { return autofill_enabled_; }
    
    // Password generator
    std::string generate_password(size_t length = 16, bool include_symbols = true);
    
    // Configuration
    void set_master_password(const std::string& password);
    bool has_master_password() const { return !master_password_.empty(); }

private:
    // Storage backends
    bool use_libsecret_;
    sqlite3* db_;
    std::string db_path_;
    std::string master_password_;
    std::vector<unsigned char> encryption_key_;
    std::vector<unsigned char> salt_;
    bool autofill_enabled_;
    
    // libsecret schema
    SecretSchema* schema_;
    
    // Database operations
    bool init_database();
    bool create_schema();
    bool save_to_sqlite(const std::string& domain, const std::string& username, const std::string& password);
    std::vector<Credential> get_from_sqlite(const std::string& domain);
    bool delete_from_sqlite(const std::string& domain, const std::string& username);
    
    // libsecret operations
    bool save_to_libsecret(const std::string& domain, const std::string& username, const std::string& password);
    std::vector<Credential> get_from_libsecret(const std::string& domain);
    bool delete_from_libsecret(const std::string& domain, const std::string& username);
    
    // Encryption helpers
    bool setup_encryption();
    std::string encrypt_password(const std::string& password);
    std::string decrypt_password(const std::string& encrypted);
    
    // Helper methods
    std::string get_db_path() const;
    std::string extract_domain(const std::string& url) const;
};
