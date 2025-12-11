#include "password_manager.h"
#include <libsecret/secret.h>
#include <sqlite3.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <random>
#include <algorithm>
#include <stdexcept>

// libsecret schema
static const SecretSchema* get_schema() {
    static const SecretSchema schema = {
        "ai.ryx.surf.password",
        SECRET_SCHEMA_NONE,
        {
            {"domain", SECRET_SCHEMA_ATTRIBUTE_STRING},
            {"username", SECRET_SCHEMA_ATTRIBUTE_STRING},
            {nullptr, SECRET_SCHEMA_ATTRIBUTE_STRING}
        }
    };
    return &schema;
}

PasswordManager::PasswordManager()
    : use_libsecret_(false)
    , db_(nullptr)
    , autofill_enabled_(true)
    , schema_(const_cast<SecretSchema*>(get_schema()))
{
    // Check if libsecret is available
    use_libsecret_ = secret_service_get_sync(SECRET_SERVICE_NONE, nullptr, nullptr) != nullptr;
    db_path_ = get_db_path();
}

PasswordManager::~PasswordManager() {
    close();
}

std::string PasswordManager::get_db_path() const {
    const char* xdg_data = std::getenv("XDG_DATA_HOME");
    std::filesystem::path base_dir;
    
    if (xdg_data) {
        base_dir = std::filesystem::path(xdg_data) / "ryxsurf";
    } else {
        const char* home = std::getenv("HOME");
        if (!home) {
            // Fallback to /tmp if HOME is not set (should not happen in normal usage)
            base_dir = std::filesystem::path("/tmp") / "ryxsurf";
        } else {
            base_dir = std::filesystem::path(home) / ".local" / "share" / "ryxsurf";
        }
    }
    
    std::filesystem::create_directories(base_dir);
    return (base_dir / "passwords.db").string();
}

bool PasswordManager::initialize(const std::string& master_password) {
    master_password_ = master_password;
    
    if (use_libsecret_) {
        // libsecret doesn't need initialization
        return true;
    }
    
    // Initialize SQLite fallback
    if (!master_password_.empty()) {
        if (!setup_encryption()) {
            return false;
        }
    }
    
    return init_database();
}

bool PasswordManager::setup_encryption() {
    if (master_password_.empty()) {
        return false;
    }
    
    std::string salt_file = db_path_ + ".salt";
    std::ifstream salt_in(salt_file, std::ios::binary);
    
    if (salt_in.is_open()) {
        salt_.resize(Crypto::SALT_SIZE);
        salt_in.read(reinterpret_cast<char*>(salt_.data()), Crypto::SALT_SIZE);
        salt_in.close();
    } else {
        salt_ = Crypto::random_bytes(Crypto::SALT_SIZE);
        std::ofstream salt_out(salt_file, std::ios::binary);
        if (salt_out.is_open()) {
            salt_out.write(reinterpret_cast<const char*>(salt_.data()), Crypto::SALT_SIZE);
            salt_out.close();
        }
    }
    
    try {
        auto [key, _] = Crypto::derive_key(master_password_, salt_);
        encryption_key_ = key;
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

bool PasswordManager::init_database() {
    if (use_libsecret_) {
        return true;  // No SQLite needed
    }
    
    int rc = sqlite3_open(db_path_.c_str(), &db_);
    if (rc != SQLITE_OK) {
        return false;
    }
    
    return create_schema();
}

bool PasswordManager::create_schema() {
    if (!db_) {
        return false;
    }
    
    const char* schema = R"(
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            username TEXT NOT NULL,
            password_encrypted BLOB NOT NULL,
            created INTEGER NOT NULL,
            last_used INTEGER NOT NULL,
            UNIQUE(domain, username)
        );
        
        CREATE INDEX IF NOT EXISTS idx_domain ON credentials(domain);
    )";
    
    char* err_msg = nullptr;
    int rc = sqlite3_exec(db_, schema, nullptr, nullptr, &err_msg);
    
    if (rc != SQLITE_OK) {
        if (err_msg) {
            sqlite3_free(err_msg);
        }
        return false;
    }
    
    return true;
}

std::string PasswordManager::encrypt_password(const std::string& password) {
    if (encryption_key_.empty()) {
        return password;  // No encryption
    }
    
    std::vector<unsigned char> plaintext(password.begin(), password.end());
    std::vector<unsigned char> encrypted = Crypto::encrypt(plaintext, encryption_key_);
    
    // Convert to base64-like string for storage
    std::string result;
    result.reserve(encrypted.size() * 2);
    for (unsigned char byte : encrypted) {
        char hex[3];
        snprintf(hex, sizeof(hex), "%02x", byte);
        result += hex;
    }
    return result;
}

std::string PasswordManager::decrypt_password(const std::string& encrypted) {
    if (encryption_key_.empty()) {
        return encrypted;  // No encryption
    }
    
    // Convert from hex string
    std::vector<unsigned char> encrypted_bytes;
    for (size_t i = 0; i < encrypted.length(); i += 2) {
        unsigned int byte;
        sscanf(encrypted.substr(i, 2).c_str(), "%02x", &byte);
        encrypted_bytes.push_back(static_cast<unsigned char>(byte));
    }
    
    std::vector<unsigned char> plaintext = Crypto::decrypt(encrypted_bytes, encryption_key_);
    return std::string(plaintext.begin(), plaintext.end());
}

bool PasswordManager::save(const std::string& domain, const std::string& username, const std::string& password) {
    if (use_libsecret_) {
        return save_to_libsecret(domain, username, password);
    } else {
        return save_to_sqlite(domain, username, password);
    }
}

bool PasswordManager::save_to_libsecret(const std::string& domain, const std::string& username, const std::string& password) {
    GError* error = nullptr;
    
    secret_password_store_sync(
        schema_,
        SECRET_COLLECTION_DEFAULT,
        "RyxSurf Password",
        password.c_str(),
        nullptr,
        &error,
        "domain", domain.c_str(),
        "username", username.c_str(),
        nullptr);
    
    if (error) {
        g_error_free(error);
        return false;
    }
    
    // Also save metadata to SQLite for fast lookup
    if (!db_) {
        init_database();
    }
    if (db_) {
        auto now = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        
        std::stringstream ss;
        ss << "INSERT OR REPLACE INTO credentials (domain, username, password_encrypted, created, last_used) "
           << "VALUES ('" << domain << "', '" << username << "', '', " << now << ", " << now << ");";
        
        sqlite3_exec(db_, ss.str().c_str(), nullptr, nullptr, nullptr);
    }
    
    return true;
}

bool PasswordManager::save_to_sqlite(const std::string& domain, const std::string& username, const std::string& password) {
    if (!db_) {
        return false;
    }
    
    std::string encrypted = encrypt_password(password);
    auto now = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    
    std::stringstream ss;
    ss << "INSERT OR REPLACE INTO credentials (domain, username, password_encrypted, created, last_used) "
       << "VALUES ('" << domain << "', '" << username << "', '" << encrypted << "', " << now << ", " << now << ");";
    
    char* err_msg = nullptr;
    int rc = sqlite3_exec(db_, ss.str().c_str(), nullptr, nullptr, &err_msg);
    
    if (rc != SQLITE_OK) {
        if (err_msg) {
            sqlite3_free(err_msg);
        }
        return false;
    }
    
    return true;
}

std::vector<Credential> PasswordManager::get(const std::string& domain) {
    if (use_libsecret_) {
        return get_from_libsecret(domain);
    } else {
        return get_from_sqlite(domain);
    }
}

std::vector<Credential> PasswordManager::get_from_libsecret(const std::string& domain) {
    std::vector<Credential> credentials;
    GError* error = nullptr;
    
    GList* items = secret_service_search_sync(
        nullptr,
        schema_,
        nullptr,
        SECRET_SEARCH_ALL,
        nullptr,
        &error,
        "domain", domain.c_str(),
        nullptr);
    
    if (error) {
        g_error_free(error);
        return credentials;
    }
    
    for (GList* item = items; item != nullptr; item = item->next) {
        SecretItem* secret_item = static_cast<SecretItem*>(item->data);
        SecretValue* value = secret_item_get_secret(secret_item);
        
        if (value) {
            const char* password = secret_value_get_text(value);
            GHashTable* attributes = secret_item_get_attributes(secret_item);
            
            const char* username = static_cast<const char*>(
                g_hash_table_lookup(attributes, "username"));
            
            if (password && username) {
                Credential cred;
                cred.domain = domain;
                cred.username = username;
                cred.password = password;
                cred.created = std::chrono::system_clock::now();
                cred.last_used = std::chrono::system_clock::now();
                credentials.push_back(cred);
            }
            
            secret_value_unref(value);
        }
    }
    
    g_list_free_full(items, g_object_unref);
    return credentials;
}

std::vector<Credential> PasswordManager::get_from_sqlite(const std::string& domain) {
    std::vector<Credential> credentials;
    
    if (!db_) {
        return credentials;
    }
    
    std::stringstream ss;
    ss << "SELECT username, password_encrypted, created, last_used FROM credentials WHERE domain = ?;";
    
    sqlite3_stmt* stmt;
    if (sqlite3_prepare_v2(db_, ss.str().c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return credentials;
    }
    
    sqlite3_bind_text(stmt, 1, domain.c_str(), -1, SQLITE_STATIC);
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const char* username = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        const char* encrypted = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        sqlite3_int64 created = sqlite3_column_int64(stmt, 2);
        sqlite3_int64 last_used = sqlite3_column_int64(stmt, 3);
        
        std::string password = decrypt_password(encrypted ? encrypted : "");
        
        Credential cred;
        cred.domain = domain;
        cred.username = username ? username : "";
        cred.password = password;
        cred.created = std::chrono::system_clock::from_time_t(created);
        cred.last_used = std::chrono::system_clock::from_time_t(last_used);
        credentials.push_back(cred);
    }
    
    sqlite3_finalize(stmt);
    return credentials;
}

std::optional<Credential> PasswordManager::get_one(const std::string& domain) {
    auto creds = get(domain);
    if (creds.empty()) {
        return std::nullopt;
    }
    
    // Return most recently used
    std::sort(creds.begin(), creds.end(),
              [](const Credential& a, const Credential& b) {
                  return a.last_used > b.last_used;
              });
    
    return creds[0];
}

bool PasswordManager::has_credentials(const std::string& domain) {
    if (use_libsecret_) {
        // Fast check using SQLite metadata if available
        if (db_) {
            std::stringstream ss;
            ss << "SELECT 1 FROM credentials WHERE domain = ? LIMIT 1;";
            sqlite3_stmt* stmt;
            if (sqlite3_prepare_v2(db_, ss.str().c_str(), -1, &stmt, nullptr) == SQLITE_OK) {
                sqlite3_bind_text(stmt, 1, domain.c_str(), -1, SQLITE_STATIC);
                bool has = sqlite3_step(stmt) == SQLITE_ROW;
                sqlite3_finalize(stmt);
                return has;
            }
        }
        // Fallback: try to get (slower)
        return !get(domain).empty();
    } else {
        if (!db_) {
            return false;
        }
        
        std::stringstream ss;
        ss << "SELECT 1 FROM credentials WHERE domain = ? LIMIT 1;";
        sqlite3_stmt* stmt;
        if (sqlite3_prepare_v2(db_, ss.str().c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
            return false;
        }
        
        sqlite3_bind_text(stmt, 1, domain.c_str(), -1, SQLITE_STATIC);
        bool has = sqlite3_step(stmt) == SQLITE_ROW;
        sqlite3_finalize(stmt);
        return has;
    }
}

bool PasswordManager::delete_credential(const std::string& domain, const std::string& username) {
    bool libsecret_ok = true;
    bool sqlite_ok = true;
    
    if (use_libsecret_) {
        libsecret_ok = delete_from_libsecret(domain, username);
    }
    
    if (db_) {
        sqlite_ok = delete_from_sqlite(domain, username);
    }
    
    return libsecret_ok && sqlite_ok;
}

bool PasswordManager::delete_from_libsecret(const std::string& domain, const std::string& username) {
    GError* error = nullptr;
    
    secret_password_clear_sync(
        schema_,
        nullptr,
        &error,
        "domain", domain.c_str(),
        "username", username.c_str(),
        nullptr);
    
    if (error) {
        g_error_free(error);
        return false;
    }
    
    return true;
}

bool PasswordManager::delete_from_sqlite(const std::string& domain, const std::string& username) {
    if (!db_) {
        return false;
    }
    
    std::stringstream ss;
    ss << "DELETE FROM credentials WHERE domain = ? AND username = ?;";
    
    sqlite3_stmt* stmt;
    if (sqlite3_prepare_v2(db_, ss.str().c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    sqlite3_bind_text(stmt, 1, domain.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, username.c_str(), -1, SQLITE_STATIC);
    
    int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    
    return rc == SQLITE_DONE;
}

void PasswordManager::update_last_used(const std::string& domain, const std::string& username) {
    if (!db_) {
        return;
    }
    
    auto now = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    
    std::stringstream ss;
    ss << "UPDATE credentials SET last_used = ? WHERE domain = ? AND username = ?;";
    
    sqlite3_stmt* stmt;
    if (sqlite3_prepare_v2(db_, ss.str().c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return;
    }
    
    sqlite3_bind_int64(stmt, 1, now);
    sqlite3_bind_text(stmt, 2, domain.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, username.c_str(), -1, SQLITE_STATIC);
    
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

std::vector<std::string> PasswordManager::list_domains() {
    std::vector<std::string> domains;
    
    if (!db_) {
        return domains;
    }
    
    const char* sql = "SELECT DISTINCT domain FROM credentials ORDER BY domain;";
    sqlite3_stmt* stmt;
    
    if (sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return domains;
    }
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const char* domain = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        if (domain) {
            domains.push_back(domain);
        }
    }
    
    sqlite3_finalize(stmt);
    return domains;
}

std::string PasswordManager::extract_domain(const std::string& url) const {
    // Simple domain extraction (should use proper URL parsing in production)
    size_t start = url.find("://");
    if (start == std::string::npos) {
        start = 0;
    } else {
        start += 3;
    }
    
    size_t end = url.find("/", start);
    if (end == std::string::npos) {
        end = url.length();
    }
    
    std::string domain = url.substr(start, end - start);
    
    // Remove port if present
    size_t colon = domain.find(":");
    if (colon != std::string::npos) {
        domain = domain.substr(0, colon);
    }
    
    return domain;
}

void PasswordManager::autofill(WebKitWebView* webview, const std::string& origin) {
    if (!autofill_enabled_ || !webview) {
        return;
    }
    
    std::string domain = extract_domain(origin);
    auto cred = get_one(domain);
    
    if (!cred.has_value()) {
        return;
    }
    
    // Use WebKit's autofill API (simplified - real implementation would use
    // WebKitFormSubmissionListener or JavaScript injection)
    // For now, this is a placeholder
    update_last_used(domain, cred->username);
}

bool PasswordManager::should_autofill(const std::string& origin) const {
    if (!autofill_enabled_) {
        return false;
    }
    
    std::string domain = extract_domain(origin);
    return has_credentials(domain);
}

std::string PasswordManager::generate_password(size_t length, bool include_symbols) {
    const std::string lowercase = "abcdefghijklmnopqrstuvwxyz";
    const std::string uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const std::string digits = "0123456789";
    const std::string symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?";
    
    std::string charset = lowercase + uppercase + digits;
    if (include_symbols) {
        charset += symbols;
    }
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, charset.length() - 1);
    
    std::string password;
    password.reserve(length);
    
    for (size_t i = 0; i < length; ++i) {
        password += charset[dis(gen)];
    }
    
    return password;
}

void PasswordManager::close() {
    if (db_) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

void PasswordManager::set_master_password(const std::string& password) {
    master_password_ = password;
    if (!password.empty() && !use_libsecret_) {
        setup_encryption();
    }
}
