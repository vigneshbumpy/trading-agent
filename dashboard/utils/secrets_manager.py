"""
Secrets Manager for encrypted storage of API keys
Uses Fernet symmetric encryption
"""

from cryptography.fernet import Fernet
import os
from pathlib import Path
from datetime import datetime


class SecretsManager:
    """Handles encrypted storage and retrieval of API keys and secrets"""

    def __init__(self, db):
        """
        Initialize SecretsManager with database connection

        Args:
            db: TradingDatabase instance
        """
        self.db = db
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get encryption key from .env or generate new one

        Returns:
            bytes: Encryption key for Fernet cipher
        """
        env_path = Path(__file__).parent.parent.parent / ".env"

        # Try to load from .env
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ENCRYPTION_KEY="):
                        key_str = line.split("=", 1)[1].strip()
                        return key_str.encode()

        # Generate new key
        key = Fernet.generate_key()

        # Save to .env
        with open(env_path, "a") as f:
            f.write(f"\n# Auto-generated encryption key for secrets\n")
            f.write(f"# DO NOT DELETE - required to decrypt API keys\n")
            f.write(f"ENCRYPTION_KEY={key.decode()}\n")

        return key

    def save_secret(self, key_name: str, value: str, provider: str = None):
        """
        Encrypt and save a secret to database

        Args:
            key_name: Name of the secret (e.g., 'OPENROUTER_API_KEY')
            value: Secret value to encrypt
            provider: Optional provider name (e.g., 'openrouter')
        """
        if not value or not value.strip():
            return

        # Encrypt the value
        encrypted = self.cipher.encrypt(value.encode())

        # Save to database
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO secrets
            (key_name, encrypted_value, provider, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        """, (key_name, encrypted, provider))
        conn.commit()
        conn.close()

    def get_secret(self, key_name: str) -> str:
        """
        Decrypt and return a secret from database

        Args:
            key_name: Name of the secret to retrieve

        Returns:
            str: Decrypted secret value or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT encrypted_value FROM secrets WHERE key_name = ?
        """, (key_name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        try:
            decrypted = self.cipher.decrypt(row[0])
            return decrypted.decode()
        except Exception as e:
            print(f"Error decrypting secret {key_name}: {e}")
            return None

    def delete_secret(self, key_name: str):
        """
        Delete a secret from database

        Args:
            key_name: Name of the secret to delete
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM secrets WHERE key_name = ?", (key_name,))
        conn.commit()
        conn.close()

    def list_secrets(self) -> list:
        """
        List all secret key names (not values)

        Returns:
            list: List of dicts with key_name, provider, updated_at
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT key_name, provider, updated_at
            FROM secrets
            ORDER BY key_name
        """)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'key_name': row[0],
                'provider': row[1],
                'updated_at': row[2]
            }
            for row in rows
        ]
