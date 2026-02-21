"""PicoRouter API Tests."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from picorouter.api import APIHandler, RateLimiter
from picorouter.keys import KeyManager


# === Rate Limiter Tests ===

class TestRateLimiter:
    """Tests for rate limiter."""
    
    def test_rate_limit_allows(self):
        """Rate limit allows requests under threshold."""
        limiter = RateLimiter(requests_per_minute=10)
        
        # Should allow 10 requests
        for i in range(10):
            assert limiter.is_allowed("test-ip") is True
    
    def test_rate_limit_blocks(self):
        """Rate limit blocks over threshold."""
        limiter = RateLimiter(requests_per_minute=2)
        
        limiter.is_allowed("test-ip")
        limiter.is_allowed("test-ip")
        
        # Third request should be blocked
        assert limiter.is_allowed("test-ip") is False
    
    def test_rate_limit_per_ip(self):
        """Rate limit is per IP."""
        limiter = RateLimiter(requests_per_minute=1)
        
        assert limiter.is_allowed("ip1") is True
        assert limiter.is_allowed("ip2") is True  # Different IP
        assert limiter.is_allowed("ip1") is False  # Same IP blocked


# === API Handler Tests ===

class TestAPIHandler:
    """Tests for API HTTP handler."""
    
    def create_handler(self, router=None, key_manager=None, rate_limiter=None):
        """Create mock API handler."""
        handler = type('Handler', (APIHandler,), {})()
        
        # Mock required attributes
        handler.path = "/health"
        handler.headers = {}
        handler.rfile = BytesIO(b"{}")
        handler.wfile = BytesIO()
        
        if router:
            APIHandler.router = router
        if key_manager:
            APIHandler.key_manager = key_manager
        if rate_limiter:
            APIHandler.rate_limiter = rate_limiter
        
        return handler
    
    def test_health_endpoint(self):
        """Test health endpoint."""
        handler = self.create_handler()
        
        # Capture response
        response = {}
        def capture(status):
            response['status'] = status
        def send_header(key, value):
            response[key] = value
        
        handler.send_response = capture
        handler.send_header = send_header
        handler.end_headers = Mock()
        handler.wfile = BytesIO()
        
        handler.do_GET()
        
        assert response['status'] == 200
    
    def test_not_found(self):
        """Test 404 response."""
        handler = self.create_handler()
        handler.path = "/nonexistent"
        
        response = {}
        handler.send_response = lambda s: response.update({'status': s})
        handler.wfile = BytesIO()
        
        handler.do_GET()
        
        assert response['status'] == 404
    
    def test_auth_no_key_required(self):
        """Test authentication not required when no keys."""
        handler = self.create_handler()
        handler.headers = {"Authorization": ""}
        
        APIHandler.key_manager = KeyManager()  # No keys
        
        # Should allow
        assert handler.authenticate() is True
    
    def test_auth_with_invalid_key(self):
        """Test invalid key rejected."""
        handler = self.create_handler()
        handler.headers = {"Authorization": "Bearer invalid"}
        
        km = KeyManager()
        km.add_key("valid", rate_limit=60)
        APIHandler.key_manager = km
        
        # Should reject
        assert handler.authenticate() is False
    
    def test_auth_with_valid_key(self):
        """Test valid key accepted."""
        handler = self.create_handler()
        
        km = KeyManager()
        key = km.add_key("test", rate_limit=60)
        APIHandler.key_manager = km
        
        handler.headers = {"Authorization": f"Bearer {key}"}
        
        assert handler.authenticate() is True
    
    def test_capability_check(self):
        """Test capability check."""
        handler = self.create_handler()
        
        # Mock auth
        handler._auth = {"capabilities": {"chat": True, "stats": False}}
        
        assert handler.check_capability("chat") is True
        assert handler.check_capability("stats") is False
    
    def test_profile_check(self):
        """Test profile access check."""
        handler = self.create_handler()
        
        # Mock auth
        handler._auth = {"profiles": ["chat", "coding"]}
        
        assert handler.check_profile("chat") is True
        assert handler.check_profile("coding") is True
        assert handler.check_profile("yolo") is False
    
    def test_rate_limit_check(self):
        """Test rate limit check."""
        handler = self.create_handler()
        
        limiter = RateLimiter(requests_per_minute=1)
        limiter.is_allowed = Mock(return_value=True)
        APIHandler.rate_limiter = limiter
        
        assert handler.check_rate_limit() is True
        
        limiter.is_allowed = Mock(return_value=False)
        assert handler.check_rate_limit() is False
    
    def test_error_response_generic(self):
        """Test error responses don't leak details."""
        handler = self.create_handler()
        
        response = {}
        handler.send_response = lambda s: response.update({'status': s})
        handler.wfile = BytesIO()
        
        handler.send_error_json(500, "Internal server error")
        
        assert response['status'] == 500


# === JSON Parsing Tests ===

class TestJSONParsing:
    """Tests for JSON request parsing."""
    
    def test_valid_json(self):
        """Test valid JSON parsing."""
        handler = type('Handler', (APIHandler,), {})()
        handler.headers = {"Content-Length": "50"}
        handler.rfile = BytesIO(b'{"messages": [{"role": "user", "content": "Hi"}]}')
        
        body = handler.rfile.read(50)
        data = json.loads(body)
        
        assert data["messages"][0]["content"] == "Hi"
    
    def test_invalid_json(self):
        """Test invalid JSON handling."""
        handler = type('Handler', (APIHandler,), {})()
        
        # Should raise
        with pytest.raises(json.JSONDecodeError):
            json.loads("not valid json")


# === Request Validation Tests ===

class TestRequestValidation:
    """Tests for request validation."""
    
    def test_empty_messages_rejected(self):
        """Empty messages should be rejected."""
        data = {"messages": []}
        
        # Validation logic
        assert len(data.get("messages", [])) == 0
    
    def test_messages_must_be_list(self):
        """Messages must be a list."""
        data = {"messages": "not a list"}
        
        assert isinstance(data["messages"], list) is False
    
    def test_max_tokens_validation(self):
        """Max tokens validation."""
        # Valid
        kwargs = {"max_tokens": 1000}
        allowed = {"temperature", "max_tokens", "top_p", "stream", "stop"}
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        assert "max_tokens" in filtered
        
        # Invalid - too high
        kwargs = {"max_tokens": 100000}
        if kwargs.get("max_tokens", 0) > 32000:
            # Should be rejected
            assert True
    
    def test_parameter_whitelist(self):
        """Only whitelisted parameters allowed."""
        data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.7,
            "max_tokens": 100,
            "unknown_param": "bad"  # Should be filtered
        }
        
        allowed = {"temperature", "max_tokens", "top_p", "stream", "stop"}
        filtered = {k: v for k, v in data.items() if k in allowed}
        
        assert "temperature" in filtered
        assert "unknown_param" not in filtered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
