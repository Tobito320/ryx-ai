"""
Password Manager - Secure credential storage using system keyring

Uses libsecret (GNOME Keyring / KDE Wallet) for secure storage.
SQLite for metadata (domains, usernames, timestamps).
Lazy-loaded to minimize memory usage.
"""

import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import time

import gi
gi.require_version('Secret', '1')
from gi.repository import Secret

# Schema for libsecret
PASSWORD_SCHEMA = Secret.Schema.new(
    "ai.ryx.surf.password",
    Secret.SchemaFlags.NONE,
    {
        "domain": Secret.SchemaAttributeType.STRING,
        "username": Secret.SchemaAttributeType.STRING,
    }
)

@dataclass
class Credential:
    domain: str
    username: str
    password: str
    created: float
    last_used: float


class PasswordManager:
    """Secure password manager using system keyring"""
    
    def __init__(self):
        self.db_path = Path.home() / ".config" / "ryxsurf" / "passwords.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for metadata"""
        self._db = sqlite3.connect(str(self.db_path))
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY,
                domain TEXT NOT NULL,
                username TEXT NOT NULL,
                created REAL NOT NULL,
                last_used REAL NOT NULL,
                UNIQUE(domain, username)
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_domain ON credentials(domain)")
        self._db.commit()
    
    def save(self, domain: str, username: str, password: str) -> bool:
        """Save credential to keyring and metadata to SQLite"""
        try:
            # Store password in system keyring
            Secret.password_store_sync(
                PASSWORD_SCHEMA,
                {"domain": domain, "username": username},
                Secret.COLLECTION_DEFAULT,
                f"RyxSurf: {domain}",
                password,
                None
            )
            
            # Store metadata in SQLite
            now = time.time()
            self._db.execute("""
                INSERT OR REPLACE INTO credentials (domain, username, created, last_used)
                VALUES (?, ?, ?, ?)
            """, (domain, username, now, now))
            self._db.commit()
            return True
        except Exception as e:
            print(f"Failed to save credential: {e}")
            return False
    
    def get(self, domain: str) -> List[Credential]:
        """Get all credentials for a domain"""
        credentials = []
        
        # Get usernames from SQLite
        cursor = self._db.execute(
            "SELECT username, created, last_used FROM credentials WHERE domain = ?",
            (domain,)
        )
        
        for username, created, last_used in cursor.fetchall():
            # Fetch password from keyring
            password = Secret.password_lookup_sync(
                PASSWORD_SCHEMA,
                {"domain": domain, "username": username},
                None
            )
            
            if password:
                credentials.append(Credential(
                    domain=domain,
                    username=username,
                    password=password,
                    created=created,
                    last_used=last_used
                ))
        
        return credentials
    
    def get_one(self, domain: str) -> Optional[Credential]:
        """Get most recently used credential for domain"""
        creds = self.get(domain)
        if creds:
            return sorted(creds, key=lambda c: c.last_used, reverse=True)[0]
        return None
    
    def has_credentials(self, domain: str) -> bool:
        """Check if we have any credentials for domain (fast, no keyring lookup)"""
        cursor = self._db.execute(
            "SELECT 1 FROM credentials WHERE domain = ? LIMIT 1",
            (domain,)
        )
        return cursor.fetchone() is not None
    
    def update_last_used(self, domain: str, username: str):
        """Update last used timestamp"""
        self._db.execute(
            "UPDATE credentials SET last_used = ? WHERE domain = ? AND username = ?",
            (time.time(), domain, username)
        )
        self._db.commit()
    
    def delete(self, domain: str, username: str) -> bool:
        """Delete a credential"""
        try:
            # Remove from keyring
            Secret.password_clear_sync(
                PASSWORD_SCHEMA,
                {"domain": domain, "username": username},
                None
            )
            
            # Remove from SQLite
            self._db.execute(
                "DELETE FROM credentials WHERE domain = ? AND username = ?",
                (domain, username)
            )
            self._db.commit()
            return True
        except Exception as e:
            print(f"Failed to delete credential: {e}")
            return False
    
    def list_domains(self) -> List[str]:
        """List all domains with saved credentials"""
        cursor = self._db.execute("SELECT DISTINCT domain FROM credentials ORDER BY domain")
        return [row[0] for row in cursor.fetchall()]
    
    def export_metadata(self) -> List[Dict]:
        """Export credential metadata (no passwords) for sync/backup"""
        cursor = self._db.execute(
            "SELECT domain, username, created, last_used FROM credentials"
        )
        return [
            {"domain": d, "username": u, "created": c, "last_used": l}
            for d, u, c, l in cursor.fetchall()
        ]
    
    def close(self):
        """Close database connection"""
        if self._db:
            self._db.close()
            self._db = None


# Lazy loading singleton
_instance: Optional[PasswordManager] = None

def get_password_manager() -> PasswordManager:
    """Get or create password manager (lazy load)"""
    global _instance
    if _instance is None:
        _instance = PasswordManager()
    return _instance

def unload_password_manager():
    """Unload password manager to free memory"""
    global _instance
    if _instance:
        _instance.close()
        _instance = None
