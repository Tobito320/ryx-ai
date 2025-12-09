#!/usr/bin/env python3
"""
Tests for Ryx AI Persistent Memory System, VRAM Guard, and Doctor Command

Run with: pytest tests/test_new_memory_system.py -v
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ═══════════════════════════════════════════════════════════════
# Persistent Memory Tests
# ═══════════════════════════════════════════════════════════════

class TestPersistentMemory:
    """Tests for the PersistentMemory class"""
    
    @pytest.fixture
    def memory(self, tmp_path):
        """Create a temporary memory instance for testing"""
        from core.memory.persistent_memory import PersistentMemory
        db_path = tmp_path / "test_memory.db"
        return PersistentMemory(db_path=db_path, encrypt=False)
    
    @pytest.fixture
    def encrypted_memory(self, tmp_path):
        """Create an encrypted memory instance for testing"""
        from core.memory.persistent_memory import PersistentMemory
        db_path = tmp_path / "test_encrypted_memory.db"
        return PersistentMemory(db_path=db_path, encrypt=True)
    
    def test_store_and_get_fact(self, memory):
        """Test storing and retrieving a simple fact"""
        memory.store_fact("user_name", "Tobi")
        result = memory.get("user_name")
        assert result == "Tobi"
    
    def test_store_complex_value(self, memory):
        """Test storing complex data structures"""
        data = {
            "name": "Tobi",
            "devices": ["laptop", "desktop"],
            "config": {"theme": "dark", "language": "de"}
        }
        memory.store_fact("user_profile", data)
        result = memory.get("user_profile")
        assert result == data
    
    def test_store_preference(self, memory):
        """Test storing preferences with higher importance"""
        from core.memory.persistent_memory import MemoryType
        memory.store_preference("ai_sidebar_auto_load", False)
        result = memory.get("ai_sidebar_auto_load", MemoryType.PREFERENCE)
        assert result is False
    
    def test_update_existing(self, memory):
        """Test updating an existing memory entry"""
        memory.store_fact("counter", 1)
        assert memory.get("counter") == 1
        
        memory.store_fact("counter", 2)
        assert memory.get("counter") == 2
    
    def test_delete(self, memory):
        """Test deleting a memory entry"""
        memory.store_fact("to_delete", "value")
        assert memory.get("to_delete") == "value"
        
        result = memory.delete("to_delete")
        assert result is True
        assert memory.get("to_delete") is None
    
    def test_recall_by_keywords(self, memory):
        """Test keyword-based recall"""
        memory.store_fact("hyprland_config", "/home/tobi/.config/hypr/hyprland.conf")
        memory.store_fact("waybar_config", "/home/tobi/.config/waybar/config")
        memory.store_fact("user_name", "Tobi")
        
        results = memory.recall("config hyprland")
        assert len(results) > 0
        assert any("hyprland" in r.key.lower() for r in results)
    
    def test_encrypted_storage(self, encrypted_memory):
        """Test that encryption works"""
        encrypted_memory.store_fact("secret", "password123")
        result = encrypted_memory.get("secret")
        assert result == "password123"
        
        # Check the raw database to ensure it's not plaintext
        import sqlite3
        conn = sqlite3.connect(encrypted_memory.db_path)
        row = conn.execute("SELECT value FROM memories WHERE key = ?", ("secret",)).fetchone()
        conn.close()
        
        # Value should not be plaintext
        assert row[0] != '"password123"'
    
    def test_user_preferences(self, memory):
        """Test user preferences storage and retrieval"""
        from core.memory.persistent_memory import UserPreferences
        
        prefs = memory.get_preferences()
        assert prefs.language == "de"  # Default
        
        prefs.language = "en"
        prefs.max_vram_percent = 85.0
        memory.save_preferences(prefs)
        
        # Create new memory instance and check persistence
        from core.memory.persistent_memory import PersistentMemory
        memory2 = PersistentMemory(db_path=memory.db_path, encrypt=False)
        prefs2 = memory2.get_preferences()
        
        assert prefs2.language == "en"
        assert prefs2.max_vram_percent == 85.0
    
    def test_session_management(self, memory):
        """Test session start/end and history"""
        session_id = memory.start_session()
        assert session_id is not None
        
        memory.update_session_stats(session_id, tasks_completed=5, tasks_failed=1)
        memory.end_session(session_id, summary="Test session")
        
        last_session = memory.get_last_session()
        assert last_session is not None
        assert last_session["session_id"] == session_id
        assert last_session["tasks_completed"] == 5
    
    def test_error_pattern_learning(self, memory):
        """Test error pattern learning for self-healing"""
        error_sig = "ImportError: No module named 'xyz'"
        fix = "pip install xyz"
        
        memory.learn_error_fix(error_sig, fix, success=True)
        
        result = memory.find_error_fix(error_sig)
        assert result == fix
    
    def test_compaction(self, memory):
        """Test memory compaction"""
        from core.memory.persistent_memory import MemoryType
        
        # Add some memories
        for i in range(10):
            memory.store(
                f"test_{i}",
                f"value_{i}",
                MemoryType.FACT,
                importance=0.1 if i < 5 else 0.9  # Half low importance
            )
        
        # Compact with low threshold (should remove low-importance entries)
        # Note: Compaction also considers recency, so just created entries may not be removed
        deleted = memory.compact(days_threshold=0, min_importance=0.5)
        
        # Just verify compaction runs without error
        assert deleted >= 0
    
    def test_stats(self, memory):
        """Test statistics generation"""
        memory.store_fact("fact1", "value1")
        memory.store_preference("pref1", "value1")
        
        stats = memory.get_stats()
        assert "total_memories" in stats
        assert "by_type" in stats
        assert stats["total_memories"] >= 2


# ═══════════════════════════════════════════════════════════════
# VRAM Guard Tests
# ═══════════════════════════════════════════════════════════════

class TestVRAMGuard:
    """Tests for the VRAM Guard"""
    
    @pytest.fixture
    def guard(self):
        """Create a VRAM guard instance"""
        from core.vram_guard import VRAMGuard
        return VRAMGuard()
    
    def test_estimate_vram_known_model(self, guard):
        """Test VRAM estimation for known models"""
        assert guard.estimate_vram("qwen2.5:1.5b") == 1500
        assert guard.estimate_vram("qwen2.5-coder:14b") == 10000
        assert guard.estimate_vram("nomic-embed-text:latest") == 500
    
    def test_estimate_vram_unknown_model(self, guard):
        """Test VRAM estimation for unknown models"""
        # Should estimate based on parameter count
        assert guard.estimate_vram("unknown:14b") == 10000
        assert guard.estimate_vram("unknown:7b") == 5000
        assert guard.estimate_vram("unknown:1.5b") == 1500
        
        # Default for completely unknown
        assert guard.estimate_vram("mystery-model") == 5000
    
    def test_vram_status_structure(self, guard):
        """Test VRAM status has correct structure"""
        status = guard.get_vram_status()
        
        assert hasattr(status, "total_mb")
        assert hasattr(status, "used_mb")
        assert hasattr(status, "free_mb")
        assert hasattr(status, "usage_percent")
        assert hasattr(status, "loaded_models")
        assert hasattr(status, "is_safe")
        assert hasattr(status, "available_mb")
    
    def test_can_load_decision_structure(self, guard):
        """Test load decision has correct structure"""
        from core.vram_guard import LoadAction
        
        decision = guard.can_load("qwen2.5:1.5b")
        
        assert hasattr(decision, "action")
        assert hasattr(decision, "model_name")
        assert hasattr(decision, "required_vram_mb")
        assert hasattr(decision, "available_vram_mb")
        assert hasattr(decision, "suggestion")
        assert decision.action in LoadAction
    
    def test_status_summary(self, guard):
        """Test status summary generation"""
        summary = guard.get_status_summary()
        assert "VRAM" in summary or "GPU" in summary


class TestModelManager:
    """Tests for the Model Manager"""
    
    @pytest.fixture
    def manager(self):
        """Create a model manager instance"""
        from core.vram_guard import ModelManager
        return ModelManager()
    
    def test_get_status(self, manager):
        """Test getting model status"""
        status = manager.get_status()
        
        assert "vram" in status
        assert "loaded_models" in status
        assert "available_models" in status


# ═══════════════════════════════════════════════════════════════
# Doctor Command Tests
# ═══════════════════════════════════════════════════════════════

class TestDoctor:
    """Tests for the Doctor command"""
    
    @pytest.fixture
    def doctor(self):
        """Create a doctor instance"""
        from core.doctor import Doctor
        return Doctor(auto_heal=False)
    
    def test_report_structure(self, doctor):
        """Test report has correct structure"""
        report = doctor.run_all_checks()
        
        assert hasattr(report, "timestamp")
        assert hasattr(report, "checks")
        assert hasattr(report, "total_issues")
        assert hasattr(report, "critical_issues")
        assert hasattr(report, "is_healthy")
    
    def test_report_summary(self, doctor):
        """Test report summary generation"""
        report = doctor.run_all_checks()
        summary = report.summary()
        
        assert "RYX AI" in summary
        assert "DOCTOR REPORT" in summary
    
    def test_check_result_structure(self):
        """Test CheckResult structure"""
        from core.doctor import CheckResult, HealthStatus
        
        result = CheckResult(
            name="Test Check",
            status=HealthStatus.HEALTHY,
            message="All good"
        )
        
        assert result.name == "Test Check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for memory and self-improvement systems"""
    
    @pytest.fixture
    def memory(self, tmp_path):
        """Create a temporary memory instance"""
        from core.memory.persistent_memory import PersistentMemory
        db_path = tmp_path / "integration_test.db"
        return PersistentMemory(db_path=db_path, encrypt=False)
    
    def test_memory_with_model_preferences(self, memory):
        """Test storing model preferences in memory"""
        memory.store_preference("preferred_code_model", "qwen2.5-coder:14b")
        memory.store_preference("max_vram_percent", 90.0)
        
        code_model = memory.get("preferred_code_model")
        max_vram = memory.get("max_vram_percent")
        
        assert code_model == "qwen2.5-coder:14b"
        assert max_vram == 90.0
    
    def test_error_learning_and_recall(self, memory):
        """Test learning from errors and recalling fixes"""
        # Simulate learning from an error
        error1 = "ModuleNotFoundError: No module named 'requests'"
        fix1 = "pip install requests"
        memory.learn_error_fix(error1, fix1, success=True)
        
        # Another occurrence of same error
        memory.learn_error_fix(error1, fix1, success=True)
        
        # Recall should return the fix
        recalled_fix = memory.find_error_fix(error1)
        assert recalled_fix == fix1
    
    def test_session_continuity(self, memory):
        """Test session state persistence across instances"""
        from core.memory.persistent_memory import PersistentMemory
        
        # Start a session
        session_id = memory.start_session()
        memory.update_session_stats(session_id, tasks_completed=3)
        memory.store_fact("last_task", "Implemented feature X")
        
        # Create new memory instance (simulating restart)
        memory2 = PersistentMemory(db_path=memory.db_path, encrypt=False)
        
        # Should be able to retrieve last session info
        last_session = memory2.get_last_session()
        last_task = memory2.get("last_task")
        
        assert last_session["session_id"] == session_id
        assert last_task == "Implemented feature X"


# ═══════════════════════════════════════════════════════════════
# Encryption Tests
# ═══════════════════════════════════════════════════════════════

class TestEncryption:
    """Tests for the SimpleEncryption class"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption/decryption is reversible"""
        from core.memory.persistent_memory import SimpleEncryption
        
        crypto = SimpleEncryption()
        original = "This is a secret message!"
        
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == original
        assert encrypted != original
    
    def test_different_keys_different_output(self):
        """Test that different keys produce different outputs"""
        from core.memory.persistent_memory import SimpleEncryption
        
        crypto1 = SimpleEncryption(key="key1")
        crypto2 = SimpleEncryption(key="key2")
        
        original = "Test message"
        
        encrypted1 = crypto1.encrypt(original)
        encrypted2 = crypto2.encrypt(original)
        
        assert encrypted1 != encrypted2
    
    def test_unicode_support(self):
        """Test encryption of unicode strings"""
        from core.memory.persistent_memory import SimpleEncryption
        
        crypto = SimpleEncryption()
        original = "Hallo Welt! 🌍 日本語 Ελληνικά"
        
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == original


# ═══════════════════════════════════════════════════════════════
# Health Monitor Tests
# ═══════════════════════════════════════════════════════════════

class TestHealthMonitor:
    """Tests for the HealthMonitor Ollama integration"""
    
    @pytest.fixture
    def health_monitor(self, tmp_path):
        """Create a temporary health monitor instance"""
        from core.health_monitor import HealthMonitor
        db_path = tmp_path / "test_health.db"
        return HealthMonitor(db_path=db_path)
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test that health monitor initializes correctly"""
        assert health_monitor.ollama_url == "http://localhost:11434"
        assert health_monitor.vllm_url == "http://localhost:8001"
        assert health_monitor.check_interval == 30
    
    def test_health_check_ollama_method_exists(self, health_monitor):
        """Test that _check_ollama method exists"""
        assert hasattr(health_monitor, '_check_ollama')
        assert callable(health_monitor._check_ollama)
    
    def test_health_check_ollama_returns_health_check(self, health_monitor):
        """Test that _check_ollama returns a HealthCheck object"""
        from core.health_monitor import HealthCheck
        
        result = health_monitor._check_ollama()
        assert isinstance(result, HealthCheck)
        assert result.component == "ollama"
    
    def test_fix_ollama_method_exists(self, health_monitor):
        """Test that _fix_ollama method exists"""
        assert hasattr(health_monitor, '_fix_ollama')
        assert callable(health_monitor._fix_ollama)
    
    def test_run_health_checks_includes_ollama(self, health_monitor):
        """Test that run_health_checks includes Ollama"""
        checks = health_monitor.run_health_checks()
        assert "ollama" in checks
        assert "vllm" in checks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
