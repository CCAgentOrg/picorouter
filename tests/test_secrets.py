"""Tests for secrets module."""

import pytest
import os
import tempfile
from picorouter.secrets import (
    SecretsManager,
    EnvBackend,
    DotEnvBackend,
    PROVIDER_KEYS,
)


class TestEnvBackend:
    """Tests for env backend."""

    def test_get_missing(self):
        """Get missing key returns None."""
        backend = EnvBackend()
        result = backend.get("NONEXISTENT_KEY_12345")
        assert result is None

    def test_set_and_get(self):
        """Set and get key."""
        os.environ["TEST_KEY_12345"] = "test_value"
        backend = EnvBackend()
        result = backend.get("TEST_KEY_12345")
        assert result == "test_value"
        del os.environ["TEST_KEY_12345"]


class TestDotEnvBackend:
    """Tests for dotenv backend."""

    def test_load_dotenv(self):
        """Load from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("TEST_KEY=value123\n")
            f.write("ANOTHER_KEY=another_value\n")
            path = f.name

        try:
            backend = DotEnvBackend(path)
            assert backend.get("TEST_KEY") == "value123"
            assert backend.get("ANOTHER_KEY") == "another_value"
        finally:
            os.unlink(path)

    def test_missing_file(self):
        """Missing file returns empty."""
        backend = DotEnvBackend("/nonexistent/.env")
        assert backend.get("ANY_KEY") is None


class TestSecretsManager:
    """Tests for SecretsManager."""

    def test_init_default(self):
        """Default init uses env backend."""
        manager = SecretsManager()
        assert manager.backend_name == "env"

    def test_get_provider_key(self):
        """Get provider key from env."""
        os.environ["KILO_API_KEY"] = "test_key_123"
        manager = SecretsManager("env")
        key = manager.get_provider_key("kilo")
        assert key == "test_key_123"
        del os.environ["KILO_API_KEY"]

    def test_get_provider_key_missing(self):
        """Missing provider key returns None."""
        manager = SecretsManager("env")
        key = manager.get_provider_key("nonexistent_provider")
        assert key is None

    def test_set_provider_key(self):
        """Set provider key."""
        manager = SecretsManager("env")
        manager.set_provider_key("kilo", "new_key_value")
        assert os.environ.get("KILO_API_KEY") == "new_key_value"

    def test_list_providers(self):
        """List all providers."""
        manager = SecretsManager("env")
        providers = manager.list_providers()
        assert len(providers) > 0
        assert all("provider" in p for p in providers)
        assert all("configured" in p for p in providers)

    def test_unknown_provider(self):
        """Unknown provider handled gracefully."""
        manager = SecretsManager("env")
        key = manager.get_provider_key("completely_unknown_provider_xyz")
        assert key is None
