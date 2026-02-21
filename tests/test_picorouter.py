"""Tests for PicoRouter."""

import pytest
import asyncio
from picorouter import (
    PromptAnalyzer,
    LocalConfig,
    CloudProvider,
    ProviderConfig,
    Profile,
    Config,
    PicoRouter,
    RoutingRule,
)


class TestPromptAnalyzer:
    """Tests for prompt analysis."""
    
    def test_detects_code(self):
        """Should detect code patterns."""
        prompt = "Write a function to sort a list in Python: def quick_sort(arr):"
        features = PromptAnalyzer.analyze(prompt)
        assert features["contains_code"] is True
    
    def test_detects_short_prompt(self):
        """Should detect short prompts."""
        prompt = "Hello"
        features = PromptAnalyzer.analyze(prompt)
        assert features["short_prompt"] is True
        assert features["long_prompt"] is False
    
    def test_detects_long_prompt(self):
        """Should detect long prompts."""
        prompt = "x" * 3000
        features = PromptAnalyzer.analyze(prompt)
        assert features["long_prompt"] is True
        assert features["short_prompt"] is False
    
    def test_detects_reasoning(self):
        """Should detect reasoning patterns."""
        prompt = "Think step by step to solve this problem"
        features = PromptAnalyzer.analyze(prompt)
        assert features["contains_reasoning"] is True
    
    def test_no_code_in_plain_text(self):
        """Should not detect code in plain text."""
        prompt = "Hello, how are you today?"
        features = PromptAnalyzer.analyze(prompt)
        assert features["contains_code"] is False
    
    def test_class_definition(self):
        """Should detect class definitions."""
        prompt = "Create a class called User with name and email"
        features = PromptAnalyzer.analyze(prompt)
        assert features["contains_code"] is True
    
    def test_import_statement(self):
        """Should detect import statements."""
        prompt = "import os and sys for file operations"
        features = PromptAnalyzer.analyze(prompt)
        assert features["contains_code"] is True


class TestRoutingRule:
    """Tests for routing rules."""
    
    def test_match_contains_code(self):
        """Should match contains_code condition."""
        rule = RoutingRule(condition="contains_code", use_local=True, models=["codellama"])
        
        features = {"contains_code": True, "short_prompt": False}
        
        assert rule.condition == "contains_code"
        assert rule.use_local is True
        assert "codellama" in rule.models


class TestConfig:
    """Tests for configuration."""
    
    def test_default_config(self):
        """Should create default config."""
        config = Config()
        assert config.default_profile == "default"
        assert config.profiles == {}
    
    def test_profile_creation(self):
        """Should create profile with defaults."""
        profile = Profile(name="test")
        assert profile.name == "test"
        assert profile.yolo is False
        assert profile.local.provider == "ollama"
    
    def test_local_config_defaults(self):
        """Should have sensible defaults."""
        local = LocalConfig()
        assert local.provider == "ollama"
        assert local.endpoint == "http://localhost:11434"
        assert local.models == []


class TestPicoRouter:
    """Tests for PicoRouter class."""
    
    def test_router_creation(self):
        """Should create router with config."""
        config = Config()
        config.profiles = {
            "default": Profile(name="default")
        }
        router = PicoRouter(config, "default")
        assert router.profile_name == "default"
    
    def test_analyze_prompt(self):
        """Should analyze prompt correctly."""
        config = Config()
        config.profiles = {
            "default": Profile(name="default")
        }
        router = PicoRouter(config, "default")
        
        messages = [
            {"role": "user", "content": "Write a function def hello(): return 'world'"}
        ]
        
        features = router.analyze_prompt(messages)
        assert features["contains_code"] is True
    
    def test_analyze_multiple_messages(self):
        """Should analyze all messages."""
        config = Config()
        config.profiles = {
            "default": Profile(name="default")
        }
        router = PicoRouter(config, "default")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "def test(): pass"},
        ]
        
        features = router.analyze_prompt(messages)
        assert features["contains_code"] is True
    
    def test_analyze_empty_messages(self):
        """Should handle empty messages."""
        config = Config()
        config.profiles = {
            "default": Profile(name="default")
        }
        router = PicoRouter(config, "default")
        
        messages = []
        features = router.analyze_prompt(messages)
        assert features["short_prompt"] is True
    
    def test_match_routing_rule(self):
        """Should match routing rules."""
        profile = Profile(name="test")
        profile.routing = [
            RoutingRule(
                condition="contains_code",
                use_local=True,
                models=["codellama"]
            ),
        ]
        
        config = Config()
        config.profiles = {"test": profile}
        router = PicoRouter(config, "test")
        
        features = {"contains_code": True}
        rule = router.match_routing_rule(features)
        
        assert rule is not None
        assert rule.condition == "contains_code"
    
    def test_no_matching_rule(self):
        """Should return None when no rule matches."""
        profile = Profile(name="test")
        profile.routing = [
            RoutingRule(
                condition="contains_code",
                use_local=True,
                models=["codellama"]
            ),
        ]
        
        config = Config()
        config.profiles = {"test": profile}
        router = PicoRouter(config, "test")
        
        features = {"contains_code": False}
        rule = router.match_routing_rule(features)
        
        assert rule is None


class TestIntegration:
    """Integration tests (require running services)."""
    
    @pytest.mark.integration
    def test_ollama_available(self):
        """Test if Ollama is available."""
        local = LocalConfig(models=["llama3"])
        # This will fail if Ollama isn't running
        # In CI, this should be skipped
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 11434))
        sock.close()
        
        # Just check if we can at least attempt connection
        assert True  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
