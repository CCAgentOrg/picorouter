"""Tests for picorouter __main__.py CLI module."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picorouter.__main__ import resolve_host


class TestResolveHost:
    """Test resolve_host function."""

    def test_resolve_0000(self):
        """Test 0.0.0.0 resolves to 0.0.0.0."""
        assert resolve_host("0.0.0.0") == "0.0.0.0"

    def test_resolve_all(self):
        """Test 'all' resolves to 0.0.0.0."""
        assert resolve_host("all") == "0.0.0.0"

    def test_resolve_asterisk(self):
        """Test '*' resolves to 0.0.0.0."""
        assert resolve_host("*") == "0.0.0.0"

    def test_resolve_localhost_ip(self):
        """Test 127.0.0.1 resolves to 127.0.0.1."""
        assert resolve_host("127.0.0.1") == "127.0.0.1"

    def test_resolve_localhost(self):
        """Test localhost resolves to 127.0.0.1."""
        assert resolve_host("localhost") == "127.0.0.1"

    @patch("picorouter.__main__.get_tailscale_ip")
    def test_resolve_tailscale(self, mock_get_ip):
        """Test tailscale resolves to Tailscale IP."""
        mock_get_ip.return_value = "100.64.0.1"
        assert resolve_host("tailscale") == "100.64.0.1"

    @patch("picorouter.__main__.get_tailscale_ip")
    def test_resolve_tailscale_not_running(self, mock_get_ip):
        """Test tailscale not running falls back to 0.0.0.0."""
        mock_get_ip.return_value = None
        assert resolve_host("tailscale") == "0.0.0.0"

    @patch("picorouter.__main__.get_all_ips")
    def test_resolve_lan(self, mock_get_ips):
        """Test lan resolves to LAN IP."""
        mock_get_ips.return_value = {"lan": "192.168.1.100"}
        assert resolve_host("lan") == "192.168.1.100"

    @patch("picorouter.__main__.get_all_ips")
    def test_resolve_lan_no_ip(self, mock_get_ips):
        """Test lan with no IP falls back to 0.0.0.0."""
        mock_get_ips.return_value = {}
        assert resolve_host("lan") == "0.0.0.0"

    def test_resolve_custom_ip(self):
        """Test custom IP is returned as-is."""
        assert resolve_host("192.168.1.50") == "192.168.1.50"

    def test_resolve_hostname(self):
        """Test hostname is returned as-is."""
        assert resolve_host("myserver.local") == "myserver.local"

    def test_resolve_strips_whitespace(self):
        """Test host is stripped of whitespace."""
        assert resolve_host("  192.168.1.50  ") == "192.168.1.50"

    def test_resolve_case_insensitive_localhost(self):
        """Test LOCALHOST resolves to 127.0.0.1."""
        assert resolve_host("LOCALHOST") == "127.0.0.1"
