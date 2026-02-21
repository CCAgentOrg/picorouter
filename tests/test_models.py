"""Tests for models module."""

import pytest
from picorouter.models import format_model_list, generate_config_from_models


class TestModels:
    """Tests for model formatting and config generation."""

    def test_format_model_list_empty(self):
        """Empty list returns no models message."""
        result = format_model_list([])
        assert "No models found" in result

    def test_format_model_list_single(self):
        """Single model formats correctly."""
        models = [{"provider": "kilo", "model": "minimax/m2.5:free"}]
        result = format_model_list(models)
        assert "kilo" in result
        assert "minimax/m2.5:free" in result

    def test_format_model_list_multiple(self):
        """Multiple models group by provider."""
        models = [
            {"provider": "kilo", "model": "minimax/m2.5:free"},
            {"provider": "kilo", "model": "minimax/m3:free"},
            {"provider": "groq", "model": "llama-3.1-70b-versatile"},
        ]
        result = format_model_list(models)
        assert "kilo" in result
        assert "groq" in result

    def test_format_model_list_truncates(self):
        """Long list truncates to 5 per provider."""
        models = [
            {"provider": "kilo", "model": f"model_{i}"}
            for i in range(10)
        ]
        result = format_model_list(models)
        assert "more" in result

    def test_generate_config_empty(self):
        """Empty models returns comment."""
        result = generate_config_from_models([])
        assert "# No models available" in result

    def test_generate_config_single(self):
        """Single model generates valid config."""
        models = [{"provider": "kilo", "model": "minimax/m2.5:free"}]
        result = generate_config_from_models(models)
        assert "profiles:" in result
        assert "kilo:" in result
        assert "minimax/m2.5:free" in result

    def test_generate_config_multiple(self):
        """Multiple models generate provider sections."""
        models = [
            {"provider": "kilo", "model": "minimax/m2.5:free"},
            {"provider": "groq", "model": "llama-3.1-70b-versatile"},
        ]
        result = generate_config_from_models(models)
        assert "profiles:" in result
        assert "default_profile: chat" in result
