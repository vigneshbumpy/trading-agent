"""Tests for production configuration system"""

import pytest
import tempfile
import os
from pathlib import Path
from dashboard.utils.database import TradingDatabase
from dashboard.utils.secrets_manager import SecretsManager
from dashboard.utils.config_manager import ConfigManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = TradingDatabase(db_path)
    yield db

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def reset_config_singleton():
    """Reset ConfigManager singleton between tests"""
    ConfigManager._instance = None
    yield
    ConfigManager._instance = None


def test_secrets_manager_encryption(temp_db):
    """Test that secrets are encrypted and decrypted correctly"""
    sm = SecretsManager(temp_db)

    # Save a secret
    sm.save_secret("TEST_KEY", "secret_value_123", "test_provider")

    # Retrieve it
    value = sm.get_secret("TEST_KEY")
    assert value == "secret_value_123"

    # Delete it
    sm.delete_secret("TEST_KEY")
    assert sm.get_secret("TEST_KEY") is None


def test_secrets_manager_list(temp_db):
    """Test listing secrets"""
    sm = SecretsManager(temp_db)

    # Add some secrets
    sm.save_secret("KEY1", "value1", "provider1")
    sm.save_secret("KEY2", "value2", "provider2")

    # List them
    secrets = sm.list_secrets()
    assert len(secrets) == 2
    key_names = [s['key_name'] for s in secrets]
    assert "KEY1" in key_names
    assert "KEY2" in key_names


def test_config_manager_get_set(temp_db, reset_config_singleton):
    """Test ConfigManager get and set operations"""
    cm = ConfigManager(temp_db)

    # Set a value
    cm.set('test_key', 'test_value')

    # Get it back
    assert cm.get('test_key') == 'test_value'

    # Should be in cache
    assert 'test_key' in cm.cache


def test_config_manager_defaults(temp_db, reset_config_singleton):
    """Test that ConfigManager provides defaults"""
    cm = ConfigManager(temp_db)

    config = cm.get_config_dict()

    # Check required keys exist
    assert 'llm_provider' in config
    assert 'quick_think_llm' in config
    assert 'deep_think_llm' in config
    assert 'max_debate_rounds' in config


def test_tier_preset_switching(temp_db, reset_config_singleton):
    """Test switching between tier presets"""
    cm = ConfigManager(temp_db)

    # Start with budget tier
    assert cm.get('llm_tier') == 'budget'
    assert cm.get('llm_provider') == 'ollama'

    # Switch to best_value
    cm.apply_tier_preset('best_value')
    assert cm.get('llm_tier') == 'best_value'
    assert cm.get('llm_provider') == 'openrouter'

    # Switch to premium
    cm.apply_tier_preset('premium')
    assert cm.get('llm_tier') == 'premium'
    assert cm.get('llm_provider') == 'anthropic'

    # Switch back to budget
    cm.apply_tier_preset('budget')
    assert cm.get('llm_tier') == 'budget'


def test_tier_presets_populated(temp_db, reset_config_singleton):
    """Test that tier presets are populated in database"""
    cm = ConfigManager(temp_db)

    presets = cm.get_tier_presets()

    # Should have 3 presets
    assert len(presets) == 3

    # Check tier names
    tier_names = [p['tier_name'] for p in presets]
    assert 'budget' in tier_names
    assert 'best_value' in tier_names
    assert 'premium' in tier_names


def test_invalid_tier_raises_error(temp_db, reset_config_singleton):
    """Test that invalid tier raises ValueError"""
    cm = ConfigManager(temp_db)

    with pytest.raises(ValueError):
        cm.apply_tier_preset('invalid_tier')


def test_api_key_check(temp_db, reset_config_singleton):
    """Test API key availability check"""
    cm = ConfigManager(temp_db)

    # No key should exist initially
    assert cm.check_api_key_available("NONEXISTENT_KEY") is False

    # Add a key
    cm.secrets_manager.save_secret("TEST_API_KEY", "test_value", "test")

    # Now it should exist
    assert cm.check_api_key_available("TEST_API_KEY") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
