"""Tests for privacy routing (ZDR) functionality."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from picorouter.providers import (
    get_zdr_models,
    get_all_models,
    get_cache_info,
    refresh_zdr_cache,
    fetch_openrouter_models,
    VirtualProvider,
    RateLimitError,
)


class TestZDRCache:
    """Test ZDR cache functions."""

    def test_get_cache_info_empty(self):
        """Test cache info when empty."""
        # Patch the module-level cache
        with patch("picorouter.providers._zdr_cache", {"models": [], "timestamp": 0}):
            info = get_cache_info()
            assert info["cached"] is False
            assert info["total_models"] == 0
            assert info["zdr_count"] == 0

    def test_get_zdr_models_empty(self):
        """Test get_zdr_models when cache is empty."""
        with patch("picorouter.providers._zdr_cache", {"models": [], "timestamp": 0}):
            models = get_zdr_models()
            assert models == []

    def test_get_all_models_empty(self):
        """Test get_all_models when cache is empty."""
        with patch("picorouter.providers._zdr_cache", {"models": [], "timestamp": 0}):
            models = get_all_models()
            assert models == []


class TestVirtualProviderPrivacy:
    """Test VirtualProvider privacy routing."""

    @pytest.mark.asyncio
    async def test_route_privacy_local_first(self):
        """Test that privacy routing tries local first."""
        # Create mock router with local provider
        mock_router = Mock()
        mock_router.profile = {"local": {"models": ["llama3"]}}
        mock_router.cloud = {}
        mock_router.try_local = AsyncMock(return_value=True)
        mock_router.local_chat = AsyncMock(
            return_value={"choices": [{"message": {"content": "Hello"}}]}
        )

        vp = VirtualProvider("picorouter/privacy", {})
        result = await vp.chat([{"role": "user", "content": "hi"}], router=mock_router)

        assert result == {"choices": [{"message": {"content": "Hello"}}]}
        mock_router.try_local.assert_called_once()
        mock_router.local_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_privacy_local_fails(self):
        """Test privacy routing when local fails."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": ["llama3"]}}
        mock_router.cloud = {}
        mock_router.try_local = AsyncMock(return_value=False)
        mock_router.local_chat = AsyncMock()

        vp = VirtualProvider("picorouter/privacy", {})

        # Should fail when no ZDR available
        with pytest.raises(Exception) as exc_info:
            await vp.chat([{"role": "user", "content": "hi"}], router=mock_router)

        assert "privacy-compliant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_privacy_with_openrouter(self):
        """Test privacy routing with OpenRouter."""
        mock_router = Mock()
        mock_router.profile = {
            "local": {"models": []}  # No local models
        }

        # Mock OpenRouter cloud provider
        mock_provider = Mock()
        mock_provider.chat = AsyncMock(
            return_value={"choices": [{"message": {"content": "ZDR response"}}]}
        )
        mock_router.cloud = {"openrouter": mock_provider}
        mock_router.try_local = AsyncMock(return_value=False)

        # Pre-populate cache with ZDR models
        mock_cache = {
            "models": [{"id": "zdr-model", "zdr": True, "price_input": 1.0}],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            result = await vp.chat(
                [{"role": "user", "content": "hi"}], router=mock_router
            )

        assert result == {"choices": [{"message": {"content": "ZDR response"}}]}

    @pytest.mark.asyncio
    async def test_route_privacy_fallback_to_cloud(self):
        """Test privacy routing falls back to cloud ZDR models."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": []}}

        # Mock cloud provider
        mock_provider = Mock()
        mock_provider.chat = AsyncMock(
            return_value={"choices": [{"message": {"content": "Cloud ZDR"}}]}
        )
        mock_router.cloud = {"openrouter": mock_provider}
        mock_router.try_local = AsyncMock(return_value=False)

        # Cache with ZDR models
        mock_cache = {
            "models": [
                {"id": "zdr-1", "zdr": True},
                {"id": "zdr-2", "zdr": True},
            ],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            result = await vp.chat(
                [{"role": "user", "content": "test"}], router=mock_router
            )

        assert result["choices"][0]["message"]["content"] == "Cloud ZDR"

    @pytest.mark.asyncio
    async def test_route_privacy_no_zdr_available(self):
        """Test privacy routing fails when no ZDR models available."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": []}}
        mock_router.cloud = {"openrouter": Mock()}
        mock_router.try_local = AsyncMock(return_value=False)

        # Cache with NO ZDR models
        mock_cache = {
            "models": [{"id": "non-zdr", "zdr": False}],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            with pytest.raises(Exception) as exc_info:
                await vp.chat([{"role": "user", "content": "hi"}], router=mock_router)

        assert "No ZDR models available" in str(exc_info.value)


class TestCacheInfo:
    """Test cache info function."""

    def test_cache_info_with_data(self):
        """Test cache info with cached data."""
        mock_cache = {
            "models": [
                {"id": "m1", "zdr": True},
                {"id": "m2", "zdr": False},
                {"id": "m3", "zdr": True},
            ],
            "timestamp": 9999999999,
        }

        with patch("picorouter.providers._zdr_cache", mock_cache):
            info = get_cache_info()
            assert info["cached"] is True
            assert info["total_models"] == 3
            assert info["zdr_count"] == 2

    def test_cache_info_expired(self):
        """Test cache info shows expired when old."""
        mock_cache = {
            "models": [{"id": "m1"}],
            # Set timestamp to 25 hours ago (TTL is 24h)
            "timestamp": time.time() - (25 * 3600),
        }

        with patch("picorouter.providers._zdr_cache", mock_cache):
            info = get_cache_info()
            assert info["expired"] is True
            assert info["age_hours"] > 24


class TestZDRModels:
    """Test ZDR model filtering."""

    def test_get_zdr_models_filters(self):
        """Test that get_zdr_models filters correctly."""
        mock_cache = {
            "models": [
                {"id": "zdr1", "zdr": True},
                {"id": "zdr2", "zdr": False},
                {"id": "zdr3", "zdr": True},
                {"id": "zdr4"},  # No zdr field
            ],
            "timestamp": 0,
        }

        with patch("picorouter.providers._zdr_cache", mock_cache):
            zdr = get_zdr_models()
            assert len(zdr) == 2
            assert all(m["zdr"] for m in zdr)

    def test_get_all_models_returns_all(self):
        """Test get_all_models returns everything."""
        mock_cache = {
            "models": [
                {"id": "m1", "zdr": True},
                {"id": "m2", "zdr": False},
            ],
            "timestamp": 0,
        }

        with patch("picorouter.providers._zdr_cache", mock_cache):
            all_models = get_all_models()
            assert len(all_models) == 2


class TestFetchOpenRouterModels:
    """Test fetch_openrouter_models with mocked HTTP."""

    def _create_mock_client(self, response_data, raise_error=None):
        """Helper to create mocked httpx.AsyncClient."""
        mock_response = Mock()
        if raise_error:
            mock_response.raise_for_status.side_effect = raise_error
        else:
            mock_response.raise_for_status = Mock()
        mock_response.json.return_value = response_data

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.mark.asyncio
    async def test_fetch_openrouter_models_success(self):
        """Test successful fetch from OpenRouter API."""
        response_data = {
            "data": [
                {
                    "id": "zdr-model-1",
                    "name": "ZDR Model 1",
                    "privacy": {"zero_retention": True},
                    "pricing": {
                        "prompt": "0.001",
                        "completion": "0.002",
                        "cached-prompt": "0.0005",
                    },
                },
                {
                    "id": "non-zdr-model",
                    "name": "Regular Model",
                    "privacy": {"zero_retention": False},
                    "pricing": {
                        "prompt": "0.005",
                        "completion": "0.01",
                        "cached-prompt": "0.001",
                    },
                },
            ]
        }

        mock_client = self._create_mock_client(response_data)

        # Use fresh empty cache
        mock_cache = {"models": [], "timestamp": 0}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch(
                "picorouter.providers._secrets.get_provider_key",
                return_value="test-api-key",
            ):
                with patch("picorouter.providers._zdr_cache", mock_cache):
                    models = await fetch_openrouter_models(force_refresh=True)

        assert len(models) == 2
        assert models[0]["id"] == "zdr-model-1"
        assert models[0]["zdr"] is True
        assert models[0]["price_input"] == 0.001
        assert models[1]["id"] == "non-zdr-model"
        assert models[1]["zdr"] is False

    @pytest.mark.asyncio
    async def test_fetch_openrouter_models_no_api_key(self):
        """Test fetch fails when no API key configured."""
        # Use empty cache - no models
        mock_cache = {"models": [], "timestamp": 0}

        with patch("picorouter.providers._secrets.get_provider_key", return_value=None):
            with patch("picorouter.providers._zdr_cache", mock_cache):
                with pytest.raises(Exception) as exc_info:
                    await fetch_openrouter_models(force_refresh=True)
                assert "OpenRouter API key not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_openrouter_models_uses_cache_when_no_key(self):
        """Test returns cached data when no API key but cache exists."""
        mock_cache = {
            "models": [{"id": "cached-model", "zdr": True}],
            "timestamp": 9999999999,
        }

        with patch("picorouter.providers._secrets.get_provider_key", return_value=None):
            with patch("picorouter.providers._zdr_cache", mock_cache):
                models = await fetch_openrouter_models(force_refresh=True)
                assert len(models) == 1
                assert models[0]["id"] == "cached-model"

    @pytest.mark.asyncio
    async def test_fetch_openrouter_models_http_error(self):
        """Test fetch handles HTTP errors gracefully."""
        mock_client = self._create_mock_client(
            {}, raise_error=Exception("HTTP 429 Rate Limited")
        )

        # Pre-populate cache
        mock_cache = {
            "models": [{"id": "fallback-model", "zdr": True}],
            "timestamp": 9999999999,
        }

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch(
                "picorouter.providers._secrets.get_provider_key",
                return_value="test-key",
            ):
                with patch("picorouter.providers._zdr_cache", mock_cache):
                    models = await fetch_openrouter_models(force_refresh=True)
                    assert len(models) == 1
                    assert models[0]["id"] == "fallback-model"

    @pytest.mark.asyncio
    async def test_fetch_openrouter_models_returns_cached_when_valid(self):
        """Test returns cached data when cache is valid and not forcing refresh."""
        mock_cache = {
            "models": [{"id": "cached-zdr", "zdr": True, "price_input": 1.0}],
            "timestamp": 9999999999,  # Far future
        }

        with patch(
            "picorouter.providers._secrets.get_provider_key", return_value="test-key"
        ):
            with patch("picorouter.providers._zdr_cache", mock_cache):
                models = await fetch_openrouter_models(force_refresh=False)
                assert len(models) == 1
                assert models[0]["id"] == "cached-zdr"


class TestRefreshZDRCache:
    """Test refresh_zdr_cache function."""

    def _create_mock_client(self, response_data):
        """Helper to create mocked httpx.AsyncClient."""
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.mark.asyncio
    async def test_refresh_zdr_cache_force_true(self):
        """Test force=True refreshes cache."""
        response_data = {
            "data": [
                {
                    "id": "new-model",
                    "name": "New ZDR Model",
                    "privacy": {"zero_retention": True},
                    "pricing": {
                        "prompt": "0.01",
                        "completion": "0.02",
                        "cached-prompt": "0.005",
                    },
                }
            ]
        }

        mock_client = self._create_mock_client(response_data)
        # Empty cache
        mock_cache = {"models": [], "timestamp": 0}

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch(
                "picorouter.providers._secrets.get_provider_key",
                return_value="test-key",
            ):
                with patch("picorouter.providers._zdr_cache", mock_cache):
                    models = await refresh_zdr_cache(force=True)
                    assert len(models) == 1
                    assert models[0]["id"] == "new-model"

    @pytest.mark.asyncio
    async def test_refresh_zdr_cache_force_false_with_valid_cache(self):
        """Test force=False uses valid cache."""
        mock_cache = {
            "models": [{"id": "valid-cached", "zdr": True}],
            "timestamp": 9999999999,
        }

        with patch(
            "picorouter.providers._secrets.get_provider_key", return_value="test-key"
        ):
            with patch("picorouter.providers._zdr_cache", mock_cache):
                models = await refresh_zdr_cache(force=False)
                assert len(models) == 1
                assert models[0]["id"] == "valid-cached"


class TestRoutePrivacyEdgeCases:
    """Test VirtualProvider._route_privacy edge cases."""

    @pytest.mark.asyncio
    async def test_route_privacy_no_openrouter_in_cloud(self):
        """Test routing when openrouter not in cloud providers."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": []}}
        mock_router.cloud = {}  # No openrouter
        mock_router.try_local = AsyncMock(return_value=False)

        mock_cache = {
            "models": [{"id": "zdr-model", "zdr": True}],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            with pytest.raises(Exception) as exc_info:
                await vp.chat([{"role": "user", "content": "hi"}], router=mock_router)
        assert "No ZDR providers available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_privacy_rate_limit_on_all_zdr(self):
        """Test when all ZDR models return rate limit."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": []}}

        mock_provider = Mock()
        mock_provider.chat = AsyncMock(side_effect=RateLimitError("Rate limited"))
        mock_router.cloud = {"openrouter": mock_provider}
        mock_router.try_local = AsyncMock(return_value=False)

        mock_cache = {
            "models": [
                {"id": "zdr-1", "zdr": True},
                {"id": "zdr-2", "zdr": True},
            ],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            with pytest.raises(Exception) as exc_info:
                await vp.chat([{"role": "user", "content": "hi"}], router=mock_router)
        assert "No ZDR providers available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_privacy_first_zdr_succeeds(self):
        """Test routing stops when first ZDR model succeeds."""
        mock_router = Mock()
        mock_router.profile = {"local": {"models": []}}

        mock_provider = Mock()
        mock_provider.chat = AsyncMock(
            side_effect=[
                {"choices": [{"message": {"content": "Success"}}]},
            ]
        )
        mock_router.cloud = {"openrouter": mock_provider}
        mock_router.try_local = AsyncMock(return_value=False)

        mock_cache = {
            "models": [
                {"id": "zdr-1", "zdr": True},
                {"id": "zdr-2", "zdr": True},
                {"id": "zdr-3", "zdr": True},
            ],
            "timestamp": 9999999999,
        }

        vp = VirtualProvider("picorouter/privacy", {})
        with patch("picorouter.providers._zdr_cache", mock_cache):
            result = await vp.chat(
                [{"role": "user", "content": "hi"}], router=mock_router
            )

        assert result["choices"][0]["message"]["content"] == "Success"
        assert mock_provider.chat.call_count == 1  # Only called once for first ZDR
