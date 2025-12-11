#pragma once

#include "session_manager.h"
#include "crypto.h"
#include <sqlite3.h>
#include <string>
#include <memory>
#include <optional>

/**
 * PersistenceManager handles encrypted SQLite storage for sessions.
 * 
 * Ownership: PersistenceManager does not own SessionManager.
 * Uses WAL mode for better concurrency.
 */
class PersistenceManager {
public:
    PersistenceManager(SessionManager* session_manager);
    ~PersistenceManager();

    // Non-copyable, movable
    PersistenceManager(const PersistenceManager&) = delete;
    PersistenceManager& operator=(const PersistenceManager&) = delete;
    PersistenceManager(PersistenceManager&&) = default;
    PersistenceManager& operator=(PersistenceManager&&) = default;

    // Database operations
    bool initialize(const std::string& master_password = "");
    void close();
    
    // Save/load operations
    bool save_all();
    bool load_all();
    
    // Individual workspace/session/tab operations
    bool save_workspace(Workspace* workspace);
    bool load_workspace(const std::string& name, Workspace* workspace);

    // Testing helper: override database path for isolated runs
    void set_db_path_for_tests(const std::string& path) { db_path_ = path; }
    
    // Autosave
    void enable_autosave(int interval_seconds = 30);
    void disable_autosave();
    
    // Configuration
    void set_master_password(const std::string& password);
    bool has_master_password() const { return !master_password_.empty(); }

private:
    SessionManager* session_manager_;
    sqlite3* db_;
    std::string db_path_;
    std::string master_password_;
    std::vector<unsigned char> encryption_key_;
    std::vector<unsigned char> salt_;
    bool autosave_enabled_;
    int autosave_interval_;
    guint autosave_timer_id_;
    
    // Make db_path_ accessible for tests
    friend class PersistenceManagerTest;
    
    // Database schema
    bool create_schema();
    bool create_tables();
    
    // Encryption helpers
    bool setup_encryption();
    std::vector<unsigned char> encrypt_data(const std::string& data);
    std::string decrypt_data(const std::vector<unsigned char>& encrypted);
    
    // SQL helpers
    bool execute_sql(const std::string& sql);
    std::string get_db_path() const;
    
    // Autosave callback
    static gboolean autosave_callback(gpointer user_data);
};
