"""Tests for config module."""

import pytest
import tempfile
import os
import yaml
from picorouter.config import (
    FileBackend,
    SQLiteConfigBackend,
    create_config_backend,
    load_config,
    find_config,
    generate_example,
    save_config,
)


class TestFileBackend:
    """Tests for file config backend."""

    def test_load_config(self):
        """Load YAML config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"key": "value", "profiles": {"chat": {}}}, f)
            path = f.name

        try:
            backend = FileBackend(path)
            config = backend.load()
            assert config["key"] == "value"
        finally:
            os.unlink(path)

    def test_save_config(self):
        """Save config to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            path = f.name

        try:
            backend = FileBackend(path)
            backend.save({"test": "data"})
            
            with open(path) as f:
                loaded = yaml.safe_load(f)
            assert loaded["test"] == "data"
        finally:
            os.unlink(path)


class TestSQLiteConfigBackend:
    """Tests for SQLite config backend."""

    def test_save_and_load(self):
        """Save and load from SQLite."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            path = f.name

        try:
            backend = SQLiteConfigBackend(path)
            backend.save({"profiles": {"chat": {}}, "default_profile": "chat"})
            config = backend.load()
            assert config["default_profile"] == "chat"
        finally:
            os.unlink(path)

    def test_get_profile(self):
        """Get specific profile."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            path = f.name

        try:
            backend = SQLiteConfigBackend(path)
            backend.save({
                "profiles": {"chat": {"local": {}}},
                "default_profile": "chat"
            })
            config = backend.load()
            profile = config.get("profiles", {}).get("chat")
            assert profile == {"local": {}}
        finally:
            os.unlink(path)


class TestCreateConfigBackend:
    """Tests for config backend factory."""

    def test_create_file(self):
        """Create file backend."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            path = f.name
        os.unlink(path)
        
        backend = create_config_backend("file", path=path)
        assert isinstance(backend, FileBackend)

    def test_create_sqlite(self):
        """Create SQLite backend."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            path = f.name
        os.unlink(path)
        
        backend = create_config_backend("sqlite", path=path)
        assert isinstance(backend, SQLiteConfigBackend)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing(self):
        """Load missing file returns empty."""
        config = load_config("/nonexistent/path.yaml")
        assert config == {}


class TestFindConfig:
    """Tests for find_config function."""

    def test_find_in_current_dir(self):
        """Find config in current directory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"key": "value"}, f)
            original = os.getcwd()
            
            try:
                os.chdir(os.path.dirname(f.name))
                config_path = os.path.basename(f.name)
                # This tests the function exists and runs
                result = find_config()
            finally:
                os.chdir(original)
                os.unlink(f.name)


class TestGenerateExample:
    """Tests for generate_example function."""

    def test_generates_valid_config(self):
        """Generate example config."""
        config = generate_example()
        
        assert "profiles" in config
        assert "default_profile" in config
        assert "chat" in config["profiles"]

    def test_has_local_and_cloud(self):
        """Config has local and cloud sections."""
        config = generate_example()
        chat = config["profiles"]["chat"]
        
        assert "local" in chat or "cloud" in chat


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_to_path(self):
        """Save config to path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.yaml")
            save_config({"test": "value"}, path)
            
            with open(path) as f:
                loaded = yaml.safe_load(f)
            assert loaded["test"] == "value"
