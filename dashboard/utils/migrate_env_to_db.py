"""
Migration script to move API keys from .env to encrypted database
Run once on first startup with new system
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from dashboard.utils.database import TradingDatabase
from dashboard.utils.secrets_manager import SecretsManager


def migrate_env_to_database():
    """Migrate API keys from .env file to encrypted database"""

    # Load .env file
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        print("No .env file found. Skipping migration.")
        return

    load_dotenv(env_path)

    # Initialize database and secrets manager
    db = TradingDatabase()
    sm = SecretsManager(db)

    # API keys to migrate
    keys_to_migrate = [
        ('OPENROUTER_API_KEY', 'openrouter'),
        ('OPENAI_API_KEY', 'openai'),
        ('ANTHROPIC_API_KEY', 'anthropic'),
        ('GOOGLE_API_KEY', 'google'),
        ('ALPHA_VANTAGE_API_KEY', 'alpha_vantage'),
        ('ALPACA_PAPER_API_KEY', 'alpaca'),
        ('ALPACA_PAPER_SECRET_KEY', 'alpaca'),
        ('ALPACA_LIVE_API_KEY', 'alpaca'),
        ('ALPACA_LIVE_SECRET_KEY', 'alpaca'),
    ]

    migrated_count = 0

    for key_name, provider in keys_to_migrate:
        value = os.getenv(key_name)
        if value:
            # Check if already exists in database
            existing = sm.get_secret(key_name)
            if not existing:
                print(f"Migrating {key_name}...")
                sm.save_secret(key_name, value, provider)
                migrated_count += 1
            else:
                print(f"Skipping {key_name} (already exists in database)")

    print(f"\n✅ Migration complete! Migrated {migrated_count} API keys to encrypted database.")
    print(f"💡 You can now remove these keys from .env (except ENCRYPTION_KEY)")


if __name__ == "__main__":
    migrate_env_to_database()
