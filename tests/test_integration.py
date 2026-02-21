"""Integration tests - requires actual infrastructure."""

import pytest
import asyncio
from picorouter.providers import LocalProvider, CloudProvider
from picorouter.router import Router


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests")


# Only run these if explicitly requested
pytestmark = pytest.mark.skipif(
    not hasattr(pytest, 'config') or not pytest.config.getoption("--run-integration", default=False),
    reason="Integration tests require --run-integration flag"
)


@pytest.mark.integration
class TestLocalProvider:
    """Integration tests with real Ollama."""
    
    @pytest.mark.asyncio
    async def test_ollama_chat(self):
        """Test real Ollama chat."""
        provider = LocalProvider({
            "provider": "ollama",
            "endpoint": "http://localhost:11434"
        })
        
        # This will fail if Ollama not running
        result = await provider.chat(
            [{"role": "user", "content": "Say 'hello' in one word"}],
            "llama3"
        )
        
        assert "message" in result
        assert "content" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """List real Ollama models."""
        provider = LocalProvider({"endpoint": "http://localhost:11434"})
        models = await provider.list_models()
        
        assert isinstance(models, list)


@pytest.mark.integration
class TestRouter:
    """Integration tests with real router."""
    
    @pytest.mark.asyncio
    async def test_full_chat_with_local(self):
        """Test complete chat with local provider."""
        config = {
            "profiles": {
                "test": {
                    "local": {
                        "provider": "ollama",
                        "endpoint": "http://localhost:11434",
                        "models": ["llama3"]
                    },
                    "cloud": {"providers": {}},
                    "yolo": False
                }
            }
        }
        
        router = Router(config, "test")
        result = await router.chat([{"role": "user", "content": "Hi"}])
        
        assert "message" in result
