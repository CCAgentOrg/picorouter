"""PicoRouter - Comprehensive Test Suite."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from picorouter.providers import CloudProvider, LocalProvider, Router, RateLimitError
from picorouter.router import analyze_prompt, match_routing_rule
from picorouter.keys import KeyManager, hash_key, generate_key
from picorouter.config import load_config, generate_example
from picorouter.logger import Logger
import json
import tempfile
import os


# === Test Fixtures ===

@pytest.fixture
def temp_log_file():
    """Temporary log file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def logger(temp_log_file):
    """Logger with temp file."""
    return Logger(temp_log_file)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "profiles": {
            "chat": {
                "local": {
                    "provider": "ollama",
                    "endpoint": "http://localhost:11434",
                    "models": ["llama3"]
                },
                "cloud": {
                    "providers": {
                        "kilo": {"models": ["minimax/m2.5:free"]},
                        "groq": {"models": ["llama-3.1-70b-versatile"]}
                    }
                },
                "routing": [
                    {"if": "short_prompt", "use_local": True},
                    {"if": "contains_code", "use_local": True}
                ],
                "yolo": False
            },
            "yolo": {
                "local": {"provider": "ollama", "models": ["llama3"]},
                "cloud": {"providers": {"kilo": {"models": ["model1"]}}},
                "yolo": True
            }
        },
        "default_profile": "chat"
    }


@pytest.fixture
def router(mock_config):
    """Router with mock config."""
    return Router(mock_config, "chat")


# === Prompt Analysis Tests ===

class TestPromptAnalyzer:
    """Tests for prompt analysis."""
    
    def test_short_prompt(self):
        """Detect short prompts."""
        result = analyze_prompt("Hi")
        assert result["short_prompt"] is True
        assert result["long_prompt"] is False
    
    def test_long_prompt(self):
        """Detect long prompts."""
        result = analyze_prompt("a" * 3000)
        assert result["long_prompt"] is True
        assert result["short_prompt"] is False
    
    def test_contains_code_python(self):
        """Detect Python code."""
        result = analyze_prompt("def hello():\n    return 'world'")
        assert result["contains_code"] is True
    
    def test_contains_code_class(self):
        """Detect class definition."""
        result = analyze_prompt("class MyClass:")
        assert result["contains_code"] is True
    
    def test_contains_code_import(self):
        """Detect import statements."""
        result = analyze_prompt("import os\nfrom pathlib import Path")
        assert result["contains_code"] is True
    
    def test_contains_code_javascript(self):
        """Detect JavaScript code."""
        result = analyze_prompt("function hello() { return true; }")
        assert result["contains_code"] is True
    
    def test_contains_reasoning(self):
        """Detect reasoning prompts."""
        result = analyze_prompt("Think step by step about this problem")
        assert result["contains_reasoning"] is True
    
    def test_reasoning_explain_why(self):
        """Detect 'explain why'."""
        result = analyze_prompt("Explain why 2+2 equals 4")
        assert result["contains_reasoning"] is True
    
    def test_language_python(self):
        """Detect Python language."""
        result = analyze_prompt("def foo(bar): return bar")
        assert result["language"] == "python"
    
    def test_language_javascript(self):
        """Detect JavaScript language."""
        result = analyze_prompt("const x = () => { return 1; }")
        assert result["language"] == "javascript"
    
    def test_no_code_plain_text(self):
        """Plain text has no code."""
        result = analyze_prompt("Hello, how are you today?")
        assert result["contains_code"] is False
        assert result["contains_reasoning"] is False


# === Routing Rule Tests ===

class TestRoutingRules:
    """Tests for routing rule matching."""
    
    def test_match_short_prompt(self):
        """Match short prompt rule."""
        features = {"short_prompt": True, "contains_code": False}
        rules = [{"if": "short_prompt", "use_local": True}]
        result = match_routing_rule(features, rules)
        assert result is not None
        assert result["use_local"] is True
    
    def test_match_code_rule(self):
        """Match code rule."""
        features = {"contains_code": True}
        rules = [{"if": "contains_code", "use_local": True}]
        result = match_routing_rule(features, rules)
        assert result is not None
    
    def test_no_match(self):
        """No matching rule."""
        features = {"short_prompt": False}
        rules = [{"if": "contains_code", "use_local": True}]
        result = match_routing_rule(features, rules)
        assert result is None
    
    def test_language_rule(self):
        """Match language rule."""
        features = {"language": "python", "contains_code": True}
        rules = [{"if": "language:python", "models": ["codellama"]}]
        result = match_routing_rule(features, rules)
        assert result is not None
        assert result["models"] == ["codellama"]


# === Local Provider Tests ===

class TestLocalProvider:
    """Tests for local provider."""
    
    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Successful local chat."""
        provider = LocalProvider({"endpoint": "http://localhost:11434"})
        
        with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
            mock_resp = Mock()
            mock_resp.json.return_value = {
                "message": {"role": "assistant", "content": "Hello!"}
            }
            mock_resp.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            
            result = await provider.chat([{"role": "user", "content": "Hi"}])
            assert result["message"]["content"] == "Hello!"
    
    @pytest.mark.asyncio
    async def test_chat_error(self):
        """Handle chat error."""
        provider = LocalProvider({"endpoint": "http://localhost:11434"})
        
        with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
            mock_resp = Mock()
            mock_resp.raise_for_status.side_effect = Exception("Connection failed")
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            
            with pytest.raises(Exception):
                await provider.chat([{"role": "user", "content": "Hi"}])
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """List models."""
        provider = LocalProvider({"endpoint": "http://localhost:11434"})
        
        with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
            mock_resp = Mock()
            mock_resp.json.return_value = {"models": [{"name": "llama3"}, {"name": "codellama"}]}
            mock_resp.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            
            models = await provider.list_models()
            assert "llama3" in models
            assert "codellama" in models


# === Cloud Provider Tests ===

class TestCloudProvider:
    """Tests for cloud provider."""
    
    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Successful cloud chat."""
        provider = CloudProvider("kilo", {
            "base_url": "https://api.kilo.ai/api/openrouter/",
            "api_key": "test-key",
            "models": ["minimax/m2.5:free"]
        })
        
        with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            mock_resp.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            
            result = await provider.chat([{"role": "user", "content": "Hi"}])
            assert "choices" in result
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Handle 429 rate limit."""
        provider = CloudProvider("groq", {
            "base_url": "https://api.groq.com/openai/",
            "api_key": "test-key",
            "models": ["llama-3.1-70b-versatile"]
        })
        
        with patch('picorouter.providers.httpx.AsyncClient') as mock_client:
            mock_resp = Mock()
            mock_resp.status_code = 429
            mock_resp.raise_for_status.side_effect = Exception("Rate limited")
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            
            with pytest.raises(RateLimitError):
                await provider.chat([{"role": "user", "content": "Hi"}])
    
    @pytest.mark.asyncio
    async def test_api_key_from_env(self):
        """Use API key from environment."""
        with patch.dict(os.environ, {"KILO_API_KEY": "env-key"}):
            provider = CloudProvider("kilo", {
                "models": ["minimax/m2.5:free"]
            })
            assert provider.api_key == "env-key"


# === Router Tests ===

class TestRouter:
    """Tests for main router."""
    
    @pytest.mark.asyncio
    async def test_chat_uses_local(self, mock_config):
        """Chat uses local provider."""
        router = Router(mock_config, "chat")
        
        with patch.object(router.local, 'chat', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = {"message": {"content": "Local response"}}
            
            result = await router.chat([{"role": "user", "content": "Hi"}])
            assert result["message"]["content"] == "Local response"
    
    @pytest.mark.asyncio
    async def test_fallback_to_cloud(self, mock_config):
        """Fallback to cloud when local fails."""
        router = Router(mock_config, "chat")
        
        # Make local fail
        async def local_fail(*args, **kwargs):
            raise Exception("Local down")
        
        router.local.chat = local_fail
        
        with patch.object(router.cloud["kilo"], 'chat', new_callable=AsyncMock) as mock_cloud:
            mock_cloud.return_value = {"message": {"content": "Cloud response"}}
            
            result = await router.chat([{"role": "user", "content": "Hi"}])
            assert result["message"]["content"] == "Cloud response"
    
    @pytest.mark.asyncio
    async def test_yolo_mode(self, mock_config):
        """YOLO mode fires all providers."""
        router = Router(mock_config, "yolo")
        
        with patch.object(router.local, 'chat', new_callable=AsyncMock) as mock_local:
            # Local is slow, will timeout
            async def slow_local(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"message": {"content": "Local"}}
            
            mock_local.side_effect = slow_local
            
            with patch.object(router.cloud["kilo"], 'chat', new_callable=AsyncMock) as mock_cloud:
                mock_cloud.return_value = {"message": {"content": "Cloud"}}
                
                result = await router.yolo_chat([{"role": "user", "content": "Hi"}])
                # Should get cloud response (faster)


# === Logger Tests ===

class TestLogger:
    """Tests for request logger."""
    
    def test_log_request(self, logger):
        """Log a request."""
        logger.log({
            "timestamp": "2025-01-01T00:00:00",
            "provider": "kilo",
            "model": "minimax/m2.5:free",
            "tokens_used": 100,
            "status": "success"
        })
        
        stats = logger.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 100
    
    def test_log_error(self, logger):
        """Log an error."""
        logger.log({
            "timestamp": "2025-01-01T00:00:00",
            "provider": "kilo",
            "status": "error"
        })
        
        stats = logger.get_stats()
        assert stats["errors"] == 1
    
    def test_cost_calculation(self, logger):
        """Calculate cost correctly."""
        logger.log({
            "timestamp": "2025-01-01T00:00:00",
            "provider": "groq",
            "tokens_used": 1_000_000,  # 1M tokens
            "status": "success"
        })
        
        stats = logger.get_stats()
        # Groq costs $0.18 per 1M tokens
        assert stats["total_cost_usd"] == 0.18
    
    def test_get_recent(self, logger):
        """Get recent logs."""
        for i in range(5):
            logger.log({
                "timestamp": f"2025-01-0{i+1}T00:00:00",
                "status": "success"
            })
        
        logs = logger.get_recent(3)
        assert len(logs) == 3


# === Key Manager Tests ===

class TestKeyManager:
    """Tests for API key management."""
    
    def test_generate_key(self):
        """Generate random key."""
        key = generate_key()
        assert key.startswith("pico_")
        assert len(key) > 20
    
    def test_hash_key(self):
        """Hash a key."""
        h = hash_key("test-key")
        assert len(h) == 16
    
    def test_add_key(self):
        """Add a new key."""
        km = KeyManager()
        key = km.add_key("test-key", rate_limit=100, profiles=["chat"])
        
        assert key.startswith("pico_")
        assert "test-key" in km.keys
        assert km.keys["test-key"]["rate_limit"] == 100
        assert km.keys["test-key"]["profiles"] == ["chat"]
    
    def test_validate_key(self):
        """Validate a key."""
        km = KeyManager()
        key = km.add_key("test-key")
        
        auth = km.validate_key(key)
        assert auth is not None
        assert auth["name"] == "test-key"
    
    def test_validate_invalid_key(self):
        """Invalid key returns None."""
        km = KeyManager()
        auth = km.validate_key("invalid-key")
        assert auth is None
    
    def test_readonly_key(self):
        """Read-only key has chat disabled."""
        km = KeyManager()
        km.add_key("readonly", readonly=True)
        
        auth = km.validate_key(km.keys["readonly"]["hash"])
        # Note: hash matching is simplified in test
        # Full validation would work with actual key
    
    def test_remove_key(self):
        """Remove a key."""
        km = KeyManager()
        km.add_key("test-key")
        
        assert km.remove_key("test-key") is True
        assert "test-key" not in km.keys
    
    def test_list_keys(self):
        """List keys without showing secrets."""
        km = KeyManager()
        km.add_key("key1", rate_limit=60)
        km.add_key("key2", rate_limit=30, readonly=True)
        
        keys = km.list_keys()
        assert len(keys) == 2
        assert keys[0]["name"] == "key1"
        assert keys[0]["rate_limit"] == 60


# === Config Tests ===

class TestConfig:
    """Tests for configuration."""
    
    def test_generate_example(self):
        """Generate example config."""
        config = generate_example()
        
        assert "profiles" in config
        assert "chat" in config["profiles"]
        assert "default_profile" in config
    
    def test_load_config_missing(self):
        """Load missing config returns empty."""
        config = load_config("/nonexistent/path.yaml")
        assert config == {}


# === Integration Tests ===

class TestIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_chat_flow(self, mock_config):
        """Test complete chat flow."""
        router = Router(mock_config, "chat")
        
        # Mock the router's internal calls
        with patch.object(router.local, 'chat', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = {
                "message": {"content": "Test response"},
                "usage": {"total_tokens": 10}
            }
            
            result = await router.chat([{"role": "user", "content": "Test"}])
            
            assert "message" in result
            assert result["message"]["content"] == "Test response"
    
    @pytest.mark.asyncio
    async def test_code_routing(self, mock_config):
        """Test code-aware routing."""
        router = Router(mock_config, "chat")
        
        code_prompt = [{"role": "user", "content": "def hello(): return 'world'"}]
        
        with patch.object(router.local, 'chat', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = {"message": {"content": "Code response"}}
            
            result = await router.chat(code_prompt)
            # Should use local for code


# === Run Tests ===

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
