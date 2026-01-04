"""
Configuration Manager for centralized config access
Provides caching, thread-safety, and instant updates
"""

from typing import Any, Dict, Optional
import threading
from datetime import datetime, timedelta
from dashboard.utils.secrets_manager import SecretsManager


class ConfigManager:
    """Centralized configuration management with caching and instant updates"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db=None):
        """Singleton pattern for global config access"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db=None):
        """Initialize ConfigManager (only runs once due to singleton)"""
        if not hasattr(self, 'initialized'):
            if db is None:
                from dashboard.utils.database import TradingDatabase
                db = TradingDatabase()

            self.db = db
            self.secrets_manager = SecretsManager(db)
            self.cache = {}
            self.cache_timestamp = None
            self.cache_ttl = timedelta(seconds=5)  # Refresh every 5 seconds
            self.initialized = True

    def _refresh_cache_if_needed(self):
        """Refresh cache if expired"""
        now = datetime.now()
        if (self.cache_timestamp is None or
            now - self.cache_timestamp > self.cache_ttl):
            self._load_from_database()
            self.cache_timestamp = now

    def _load_from_database(self):
        """Load all settings from database into cache"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()

        self.cache.clear()
        for key, value in rows:
            # Try to convert to int if possible
            try:
                self.cache[key] = int(value)
            except (ValueError, TypeError):
                self.cache[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with caching

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        self._refresh_cache_if_needed()
        return self.cache.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set configuration value and save to database

        Args:
            key: Configuration key
            value: Configuration value
        """
        # Convert to string for database storage
        value_str = str(value)

        # Save to database
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
        """, (key, value_str))
        conn.commit()
        conn.close()

        # Update cache immediately
        self.cache[key] = value
        self.cache_timestamp = datetime.now()

    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dict for TradingAgentsGraph

        Returns:
            dict: Complete configuration dictionary
        """
        # Start with DEFAULT_CONFIG as base
        from tradingagents.default_config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.copy()

        # Refresh cache
        self._refresh_cache_if_needed()

        # Override with database settings
        for key, value in self.cache.items():
            config[key] = value

        # Ensure LLM defaults for budget tier
        llm_defaults = {
            'llm_provider': 'ollama',
            'backend_url': 'http://localhost:11434/v1',
            'quick_think_llm': 'llama3.2',
            'deep_think_llm': 'qwen2.5:32b',
        }

        for key, default_value in llm_defaults.items():
            if key not in config or not config[key]:
                config[key] = default_value

        # Map model keys (database uses quick_think_model, graph uses quick_think_llm)
        if 'quick_think_model' in config:
            config['quick_think_llm'] = config['quick_think_model']
        if 'deep_think_model' in config:
            config['deep_think_llm'] = config['deep_think_model']

        # When using Ollama, use local vendors for news (openai vendor requires special API)
        if config.get('llm_provider') == 'ollama':
            if 'data_vendors' not in config:
                config['data_vendors'] = {}
            # Override news_data to use local (reddit) since openai vendor requires web_search
            config['data_vendors']['news_data'] = 'local'

        return config

    def apply_tier_preset(self, tier_name: str):
        """
        Apply a tier preset (budget/best_value/premium)

        Args:
            tier_name: Tier to apply (budget, best_value, premium)
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT provider, backend_url, quick_think_model, deep_think_model
            FROM llm_presets WHERE tier_name = ?
        """, (tier_name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"Unknown tier: {tier_name}")

        provider, backend_url, quick_model, deep_model = row

        # Update all settings atomically
        self.set('llm_tier', tier_name)
        self.set('llm_provider', provider)
        if backend_url:
            self.set('backend_url', backend_url)
        self.set('quick_think_model', quick_model)
        self.set('deep_think_model', deep_model)
        # Also set the _llm versions for compatibility
        self.set('quick_think_llm', quick_model)
        self.set('deep_think_llm', deep_model)

    def get_current_tier(self) -> Optional[str]:
        """
        Get current LLM tier

        Returns:
            str: Current tier name or None
        """
        return self.get('llm_tier')

    def get_tier_presets(self) -> list:
        """
        Get all available tier presets

        Returns:
            list: List of tier preset dicts
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tier_name, display_name, provider, quick_think_model,
                   deep_think_model, requires_api_key, api_key_name,
                   estimated_cost_month, speed_rating, quality_rating,
                   is_recommended
            FROM llm_presets
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'tier_name': row[0],
                'display_name': row[1],
                'provider': row[2],
                'quick_think_model': row[3],
                'deep_think_model': row[4],
                'requires_api_key': bool(row[5]),
                'api_key_name': row[6],
                'estimated_cost_month': row[7],
                'speed_rating': row[8],
                'quality_rating': row[9],
                'is_recommended': bool(row[10])
            }
            for row in rows
        ]

    def check_api_key_available(self, key_name: str) -> bool:
        """
        Check if an API key is available (either in secrets or environment)

        Args:
            key_name: Name of the API key to check

        Returns:
            bool: True if key is available
        """
        # Check secrets first
        secret = self.secrets_manager.get_secret(key_name)
        if secret:
            return True

        # Check environment variables
        import os
        return bool(os.getenv(key_name))

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get API key from secrets or environment

        Args:
            key_name: Name of the API key

        Returns:
            str: API key value or None
        """
        # Try secrets first
        secret = self.secrets_manager.get_secret(key_name)
        if secret:
            return secret

        # Fall back to environment
        import os
        return os.getenv(key_name)
