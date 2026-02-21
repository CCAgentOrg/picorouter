"""Tests for storage module."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from picorouter.storage import JSONLBackend, SQLiteBackend, create_backend


class TestJSONLBackend:
    """Tests for JSONL storage backend."""

    def test_log_entry(self):
        """Log an entry to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = JSONLBackend(log_file)

            backend.log({
                "timestamp": "2025-01-01T00:00:00",
                "provider": "kilo",
                "model": "minimax/m2.5:free",
                "tokens_used": 100,
                "status": "success"
            })

            stats = backend.get_stats()
            assert stats["total_requests"] == 1
            assert stats["total_tokens"] == 100

    def test_log_error(self):
        """Log an error entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = JSONLBackend(log_file)

            backend.log({
                "timestamp": "2025-01-01T00:00:00",
                "provider": "kilo",
                "status": "error"
            })

            stats = backend.get_stats()
            assert stats["errors"] == 1

    def test_get_recent(self):
        """Get recent entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = JSONLBackend(log_file)

            for i in range(5):
                backend.log({
                    "timestamp": f"2025-01-0{i+1}T00:00:00",
                    "provider": "kilo",
                    "status": "success"
                })

            recent = backend.get_recent(3)
            assert len(recent) == 3

    def test_stats_by_provider(self):
        """Stats track by provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = JSONLBackend(log_file)

            backend.log({"provider": "kilo", "tokens_used": 100, "status": "success"})
            backend.log({"provider": "groq", "tokens_used": 200, "status": "success"})

            stats = backend.get_stats()
            assert stats["by_provider"]["kilo"] == 1
            assert stats["by_provider"]["groq"] == 1

    def test_cost_calculation(self):
        """Cost calculated correctly per provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = JSONLBackend(log_file)

            # Groq: $0.18 per 1M tokens
            backend.log({
                "provider": "groq",
                "tokens_used": 1_000_000,
                "status": "success"
            })

            stats = backend.get_stats()
            assert stats["total_cost_usd"] == 0.18


class TestSQLiteBackend:
    """Tests for SQLite storage backend."""

    def test_log_entry(self):
        """Log entry to SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test.db")
            backend = SQLiteBackend(db_file)

            backend.log({
                "timestamp": "2025-01-01T00:00:00",
                "provider": "kilo",
                "model": "minimax/m2.5:free",
                "tokens_used": 100,
                "status": "success"
            })

            stats = backend.get_stats()
            assert stats["total_requests"] == 1

    def test_get_recent(self):
        """Get recent from SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test.db")
            backend = SQLiteBackend(db_file)

            for i in range(5):
                backend.log({
                    "timestamp": f"2025-01-0{i+1}T00:00:00",
                    "provider": "kilo",
                    "status": "success"
                })

            recent = backend.get_recent(3)
            assert len(recent) == 3


class TestCreateBackend:
    """Tests for backend factory."""

    def test_create_jsonl(self):
        """Create JSONL backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.jsonl")
            backend = create_backend("jsonl", log_file=log_file)
            assert isinstance(backend, JSONLBackend)

    def test_create_sqlite(self):
        """Create SQLite backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test.db")
            backend = create_backend("sqlite", db_file=db_file)
            assert isinstance(backend, SQLiteBackend)
