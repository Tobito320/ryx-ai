#pragma once

#include <string>
#include <filesystem>
#include <memory>

class Tab;  // Forward declaration

/**
 * SnapshotManager handles tab snapshot generation and restoration.
 * 
 * Snapshots are stored as PNG images + minimal HTML state.
 * Ownership: SnapshotManager does not own Tab objects.
 */
class SnapshotManager {
public:
    SnapshotManager();
    ~SnapshotManager();

    // Non-copyable, movable
    SnapshotManager(const SnapshotManager&) = delete;
    SnapshotManager& operator=(const SnapshotManager&) = delete;
    SnapshotManager(SnapshotManager&&) = default;
    SnapshotManager& operator=(SnapshotManager&&) = default;

    // Snapshot operations
    std::string create_snapshot(Tab* tab);
    bool restore_snapshot(Tab* tab, const std::string& snapshot_path);
    void delete_snapshot(const std::string& snapshot_path);
    
    // Snapshot path management
    std::string get_snapshot_path(const std::string& tab_id) const;
    bool snapshot_exists(const std::string& snapshot_path) const;

private:
    std::filesystem::path snapshot_dir_;
    
    void ensure_snapshot_dir();
    std::string generate_tab_id(Tab* tab) const;
};
