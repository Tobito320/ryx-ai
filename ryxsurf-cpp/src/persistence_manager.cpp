#include "persistence_manager.h"
#include "workspace.h"
#include "session.h"
#include "tab.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <map>
#include <glib.h>
#include <sqlite3.h>
#include <stdexcept>

PersistenceManager::PersistenceManager(SessionManager* session_manager)
    : session_manager_(session_manager)
    , db_(nullptr)
    , autosave_enabled_(false)
    , autosave_interval_(30)
    , autosave_timer_id_(0)
{
    db_path_ = get_db_path();
}

PersistenceManager::~PersistenceManager() {
    disable_autosave();
    close();
}

std::string PersistenceManager::get_db_path() const {
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
    return (base_dir / "sessions.db").string();
}

bool PersistenceManager::initialize(const std::string& master_password) {
    master_password_ = master_password;
    
    // Initialize libsodium
    try {
        Crypto::init();
    } catch (const std::exception& e) {
        return false;
    }
    
    // Setup encryption
    if (!master_password_.empty()) {
        if (!setup_encryption()) {
            return false;
        }
    }
    
    // Open database
    int rc = sqlite3_open(db_path_.c_str(), &db_);
    if (rc != SQLITE_OK) {
        return false;
    }
    
    // Enable WAL mode
    execute_sql("PRAGMA journal_mode=WAL;");
    execute_sql("PRAGMA synchronous=NORMAL;");
    execute_sql("PRAGMA foreign_keys=ON;");
    
    // Create schema
    return create_schema();
}

bool PersistenceManager::setup_encryption() {
    if (master_password_.empty()) {
        return false;
    }
    
    // Try to load existing salt from database file header or separate file
    std::string salt_file = db_path_ + ".salt";
    std::ifstream salt_in(salt_file, std::ios::binary);
    
    if (salt_in.is_open()) {
        salt_.resize(Crypto::SALT_SIZE);
        salt_in.read(reinterpret_cast<char*>(salt_.data()), Crypto::SALT_SIZE);
        salt_in.close();
    } else {
        // Generate new salt
        salt_ = Crypto::random_bytes(Crypto::SALT_SIZE);
        std::ofstream salt_out(salt_file, std::ios::binary);
        if (salt_out.is_open()) {
            salt_out.write(reinterpret_cast<const char*>(salt_.data()), Crypto::SALT_SIZE);
            salt_out.close();
        }
    }
    
    // Derive key
    try {
        auto [key, _] = Crypto::derive_key(master_password_, salt_);
        encryption_key_ = key;
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

bool PersistenceManager::create_schema() {
    return create_tables();
}

bool PersistenceManager::create_tables() {
    const char* schema = R"(
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_overview INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
            UNIQUE(workspace_id, name)
        );
        
        CREATE TABLE IF NOT EXISTS tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            snapshot_path TEXT,
            last_active INTEGER NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_tabs_session ON tabs(session_id);
    )";
    
    return execute_sql(schema);
}

bool PersistenceManager::execute_sql(const std::string& sql) {
    if (!db_) {
        return false;
    }
    
    char* err_msg = nullptr;
    int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &err_msg);
    
    if (rc != SQLITE_OK) {
        if (err_msg) {
            sqlite3_free(err_msg);
        }
        return false;
    }
    
    return true;
}

std::vector<unsigned char> PersistenceManager::encrypt_data(const std::string& data) {
    if (encryption_key_.empty()) {
        // Return plaintext as bytes if no encryption
        return std::vector<unsigned char>(data.begin(), data.end());
    }
    
    std::vector<unsigned char> plaintext(data.begin(), data.end());
    return Crypto::encrypt(plaintext, encryption_key_);
}

std::string PersistenceManager::decrypt_data(const std::vector<unsigned char>& encrypted) {
    if (encryption_key_.empty()) {
        // Return as string if no encryption
        return std::string(encrypted.begin(), encrypted.end());
    }
    
    std::vector<unsigned char> plaintext = Crypto::decrypt(encrypted, encryption_key_);
    return std::string(plaintext.begin(), plaintext.end());
}

bool PersistenceManager::save_all() {
    if (!db_) {
        return false;
    }
    
    // Begin transaction
    execute_sql("BEGIN TRANSACTION;");
    
    // Clear existing data
    execute_sql("DELETE FROM tabs;");
    execute_sql("DELETE FROM sessions;");
    execute_sql("DELETE FROM workspaces;");
    
    // Save all workspaces
    for (size_t i = 0; i < session_manager_->get_workspace_count(); ++i) {
        Workspace* ws = session_manager_->get_workspace(i);
        if (ws) {
            bool is_empty_default = ws->get_name() == "Main" &&
                                   ws->get_session_count() == 1 &&
                                   ws->get_session(0)->is_overview() &&
                                   ws->get_session(0)->get_tab_count() == 0;
            if (is_empty_default) {
                continue;
            }
            if (!save_workspace(ws)) {
                execute_sql("ROLLBACK;");
                return false;
            }
        }
    }
    
    // Commit transaction
    execute_sql("COMMIT;");
    return true;
}

bool PersistenceManager::save_workspace(Workspace* workspace) {
    if (!workspace || !db_) {
        return false;
    }
    
    // Insert workspace using parameterized query
    const char* sql = "INSERT OR REPLACE INTO workspaces (name, created_at, updated_at) VALUES (?, ?, ?);";
    sqlite3_stmt* stmt;
    
    if (sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    auto created = std::chrono::duration_cast<std::chrono::seconds>(
        workspace->get_created_at().time_since_epoch()).count();
    auto updated = std::chrono::duration_cast<std::chrono::seconds>(
        workspace->get_updated_at().time_since_epoch()).count();
    
    sqlite3_bind_text(stmt, 1, workspace->get_name().c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int64(stmt, 2, created);
    sqlite3_bind_int64(stmt, 3, updated);
    
    if (sqlite3_step(stmt) != SQLITE_DONE) {
        sqlite3_finalize(stmt);
        return false;
    }
    
    sqlite3_int64 workspace_id = sqlite3_last_insert_rowid(db_);
    sqlite3_finalize(stmt);
    
    // Save sessions
    const char* session_sql = "INSERT OR REPLACE INTO sessions (workspace_id, name, is_overview, created_at, updated_at) VALUES (?, ?, ?, ?, ?);";
    
    for (size_t i = 0; i < workspace->get_session_count(); ++i) {
        Session* session = workspace->get_session(i);
        if (!session) {
            continue;
        }
        
        if (sqlite3_prepare_v2(db_, session_sql, -1, &stmt, nullptr) != SQLITE_OK) {
            continue;
        }
        
        auto s_created = std::chrono::duration_cast<std::chrono::seconds>(
            session->get_created_at().time_since_epoch()).count();
        auto s_updated = std::chrono::duration_cast<std::chrono::seconds>(
            session->get_updated_at().time_since_epoch()).count();
        
        sqlite3_bind_int64(stmt, 1, workspace_id);
        sqlite3_bind_text(stmt, 2, session->get_name().c_str(), -1, SQLITE_STATIC);
        sqlite3_bind_int(stmt, 3, session->is_overview() ? 1 : 0);
        sqlite3_bind_int64(stmt, 4, s_created);
        sqlite3_bind_int64(stmt, 5, s_updated);
        
        if (sqlite3_step(stmt) != SQLITE_DONE) {
            sqlite3_finalize(stmt);
            continue;
        }
        
        sqlite3_int64 session_id = sqlite3_last_insert_rowid(db_);
        sqlite3_finalize(stmt);
        
        // Save tabs using parameterized query
        const char* tab_sql = "INSERT INTO tabs (session_id, url, title, snapshot_path, last_active, position) VALUES (?, ?, ?, ?, ?, ?);";
        
        for (size_t j = 0; j < session->get_tab_count(); ++j) {
            Tab* tab = session->get_tab(j);
            if (!tab) {
                continue;
            }
            
            if (sqlite3_prepare_v2(db_, tab_sql, -1, &stmt, nullptr) != SQLITE_OK) {
                continue;
            }
            
            // Use system_clock time_point for persistence
            auto last_active = std::chrono::duration_cast<std::chrono::seconds>(
                tab->get_last_active_system().time_since_epoch()).count();
            
            sqlite3_bind_int64(stmt, 1, session_id);
            sqlite3_bind_text(stmt, 2, tab->get_url().c_str(), -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 3, tab->get_title().c_str(), -1, SQLITE_STATIC);
            sqlite3_bind_text(stmt, 4, tab->get_snapshot_path().c_str(), -1, SQLITE_STATIC);
            sqlite3_bind_int64(stmt, 5, last_active);
            sqlite3_bind_int(stmt, 6, j);
            
            if (sqlite3_step(stmt) != SQLITE_DONE) {
                sqlite3_finalize(stmt);
                continue;
            }
            
            sqlite3_finalize(stmt);
        }
    }
    
    return true;
}

bool PersistenceManager::load_all() {
    if (!db_) {
        return false;
    }

    // Start from a clean slate to avoid carrying default workspaces into loaded state
    session_manager_->reset(false);
    
    // Load workspaces
    const char* sql = "SELECT id, name, created_at, updated_at FROM workspaces ORDER BY id;";
    sqlite3_stmt* stmt;
    
    if (sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }
    
    std::map<sqlite3_int64, Workspace*> workspace_map;
    
    bool loaded_any = false;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        loaded_any = true;
        sqlite3_int64 id = sqlite3_column_int64(stmt, 0);
        const char* name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        sqlite3_int64 created = sqlite3_column_int64(stmt, 2);
        sqlite3_int64 updated = sqlite3_column_int64(stmt, 3);
        
        Workspace* ws = session_manager_->add_workspace(name ? name : "");
        if (ws) {
            if (created > 0) {
                ws->set_created_at(std::chrono::system_clock::from_time_t(static_cast<time_t>(created)));
            }
            if (updated > 0) {
                ws->set_updated_at(std::chrono::system_clock::from_time_t(static_cast<time_t>(updated)));
            }
        }
        workspace_map[id] = ws;
        
        // Load sessions for this workspace using parameterized query
        const char* session_sql = "SELECT id, name, is_overview, created_at, updated_at FROM sessions WHERE workspace_id = ? ORDER BY id;";
        sqlite3_stmt* session_stmt;
        
        if (sqlite3_prepare_v2(db_, session_sql, -1, &session_stmt, nullptr) == SQLITE_OK) {
            sqlite3_bind_int64(session_stmt, 1, id);
            
            while (sqlite3_step(session_stmt) == SQLITE_ROW) {
                sqlite3_int64 session_id = sqlite3_column_int64(session_stmt, 0);
                const char* s_name = reinterpret_cast<const char*>(sqlite3_column_text(session_stmt, 1));
                int is_overview = sqlite3_column_int(session_stmt, 2);
                
                Session* session = ws->add_session(s_name ? s_name : "");
                session->set_overview(is_overview != 0);
                sqlite3_int64 s_created = sqlite3_column_int64(session_stmt, 3);
                sqlite3_int64 s_updated = sqlite3_column_int64(session_stmt, 4);
                if (s_created > 0) {
                    session->set_created_at(std::chrono::system_clock::from_time_t(static_cast<time_t>(s_created)));
                }
                if (s_updated > 0) {
                    session->set_updated_at(std::chrono::system_clock::from_time_t(static_cast<time_t>(s_updated)));
                }
                
                // Load tabs for this session using parameterized query
                const char* tab_sql = "SELECT url, title, snapshot_path, last_active, position FROM tabs WHERE session_id = ? ORDER BY position;";
                sqlite3_stmt* tab_stmt;
                
                if (sqlite3_prepare_v2(db_, tab_sql, -1, &tab_stmt, nullptr) == SQLITE_OK) {
                    sqlite3_bind_int64(tab_stmt, 1, session_id);
                    
                    while (sqlite3_step(tab_stmt) == SQLITE_ROW) {
                        const char* url = reinterpret_cast<const char*>(sqlite3_column_text(tab_stmt, 0));
                        const char* title = reinterpret_cast<const char*>(sqlite3_column_text(tab_stmt, 1));
                        const char* snapshot = reinterpret_cast<const char*>(sqlite3_column_text(tab_stmt, 2));
                        sqlite3_int64 last_active = sqlite3_column_int64(tab_stmt, 3);
                        
                        Tab* tab = session->add_tab(url ? url : "");
                        tab->set_title(title ? title : "");
                        if (snapshot) {
                            tab->set_snapshot_path(snapshot);
                        }
                        if (last_active > 0) {
                            tab->set_last_active_system(std::chrono::system_clock::from_time_t(static_cast<time_t>(last_active)));
                        }
                    }
                    sqlite3_finalize(tab_stmt);
                }
            }
            sqlite3_finalize(session_stmt);
        }
    }
    
    sqlite3_finalize(stmt);

    if (!loaded_any) {
        // Recreate default workspace if nothing was stored
        session_manager_->reset(true);
    }
    return true;
}

void PersistenceManager::enable_autosave(int interval_seconds) {
    disable_autosave();
    autosave_enabled_ = true;
    autosave_interval_ = interval_seconds;
    autosave_timer_id_ = g_timeout_add_seconds(
        interval_seconds,
        autosave_callback,
        this);
}

void PersistenceManager::disable_autosave() {
    if (autosave_timer_id_ != 0) {
        g_source_remove(autosave_timer_id_);
        autosave_timer_id_ = 0;
    }
    autosave_enabled_ = false;
}

gboolean PersistenceManager::autosave_callback(gpointer user_data) {
    PersistenceManager* pm = static_cast<PersistenceManager*>(user_data);
    pm->save_all();
    return TRUE;  // Keep timer running
}

void PersistenceManager::close() {
    disable_autosave();
    if (db_) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

void PersistenceManager::set_master_password(const std::string& password) {
    master_password_ = password;
    if (!password.empty()) {
        setup_encryption();
    } else {
        encryption_key_.clear();
        salt_.clear();
    }
}

bool PersistenceManager::load_workspace(const std::string& name, Workspace* workspace) {
    (void)name;
    (void)workspace;
    // Implementation for loading single workspace
    // For now, load_all handles everything
    return false;
}
