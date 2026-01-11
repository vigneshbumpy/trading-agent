"""
LLM Response Caching Service
Caches analyst outputs to reduce API costs and improve speed for repeated queries.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

class LLMCache:
    def __init__(self, db_path: str = "dashboard/data/llm_cache.db", ttl_hours: int = 24):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.init_db()

    def init_db(self):
        """Initialize cache database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # Index for cleanup (though key is PK)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
        conn.commit()
        conn.close()

    def _generate_key(self, prompt: str, model: str, extra_params: Dict = None) -> str:
        """Generate unique hash for the request"""
        content = f"{prompt}|{model}|{json.dumps(extra_params or {}, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, prompt: str, model: str, extra_params: Dict = None) -> Optional[str]:
        """Retrieve cached response if valid"""
        key = self._generate_key(prompt, model, extra_params)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT response, created_at FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            response, created_at = row
            created_dt = datetime.fromisoformat(created_at)
            if datetime.now() - created_dt < timedelta(hours=self.ttl_hours):
                return response
            else:
                # Expired
                self.delete(key)
        
        return None

    def set(self, prompt: str, model: str, response: str, extra_params: Dict = None):
        """Cache unique response"""
        key = self._generate_key(prompt, model, extra_params)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cache (key, response, created_at)
            VALUES (?, ?, ?)
        """, (key, response, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def delete(self, key: str):
        """Remove specific key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def clear_expired(self):
        """Remove all expired entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        cursor.execute("DELETE FROM cache WHERE created_at < ?", (cutoff,))
        conn.commit()
        conn.close()

# Global instance
llm_cache = LLMCache()
