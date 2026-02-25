"""Tests for picorouter tailscale module."""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picorouter.tailscale import (
    get_tailscale_ip,
    get_all_ips,
    is_tailscale_running,
    print_network_info,
)


class TestGetTailscaleIP:
    """Test get_tailscale_ip function."""

    @patch("picorouter.tailscale.subprocess.run")
    def test_get_tailscale_ip_success(self, mock_run):
        """Test successful Tailscale IP retrieval from Self."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Self": {"TailscaleIPs": ["100.64.0.1"]}}'
        mock_run.return_value = mock_result

        result = get_tailscale_ip()
        assert result == "100.64.0.1"

    @patch("picorouter.tailscale.subprocess.run")
    def test_get_tailscale_ip_peer(self, mock_run):
        """Test Tailscale IP from Peer."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Peer": {"100.64.0.2": {"HostName": "host"}}}'
        mock_run.return_value = mock_result

        result = get_tailscale_ip()
        assert result == "100.64.0.2"

    @patch("picorouter.tailscale.subprocess.run")
    def test_get_tailscale_ip_no_tailscale(self, mock_run):
        """Test when Tailscale is not running (first method fails)."""
        mock_run.side_effect = Exception("Command failed")

        result = get_tailscale_ip()
        assert result is None

    @patch("picorouter.tailscale.subprocess.run")
    def test_get_tailscale_ip_json_error(self, mock_run):
        """Test with invalid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        result = get_tailscale_ip()
        assert result is None

    @patch("picorouter.tailscale.subprocess.run")
    def test_get_tailscale_ip_fallback_method(self, mock_run):
        """Test fallback to tailscale ip command."""
        # First call (status) fails, second call (ip) succeeds
        mock_run.side_effect = [
            Exception("status failed"),
            MagicMock(returncode=0, stdout="100.64.0.3\n"),
        ]

        result = get_tailscale_ip()
        assert result == "100.64.0.3"


class TestGetAllIPs:
    """Test get_all_ips function."""

    @patch("picorouter.tailscale.get_tailscale_ip")
    def test_get_all_ips_includes_defaults(self, mock_get_ip):
        """Test that defaults are included."""
        mock_get_ip.return_value = None

        result = get_all_ips()

        assert "localhost" in result
        assert result["localhost"] == "127.0.0.1"
        assert "all" in result
        assert result["all"] == "0.0.0.0"

    @patch("picorouter.tailscale.get_tailscale_ip")
    def test_get_all_ips_includes_tailscale(self, mock_get_ip):
        """Test that Tailscale IP is included when present."""
        mock_get_ip.return_value = "100.64.0.1"

        result = get_all_ips()

        assert "tailscale" in result
        assert result["tailscale"] == "100.64.0.1"


class TestIsTailscaleRunning:
    """Test is_tailscale_running function."""

    @patch("picorouter.tailscale.subprocess.run")
    def test_is_tailscale_running_true(self, mock_run):
        """Test when Tailscale is running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = is_tailscale_running()
        assert result is True

    @patch("picorouter.tailscale.subprocess.run")
    def test_is_tailscale_running_false(self, mock_run):
        """Test when Tailscale is not running."""
        mock_run.side_effect = Exception("Command failed")

        result = is_tailscale_running()
        assert result is False


class TestPrintNetworkInfo:
    """Test print_network_info function."""

    @patch("picorouter.tailscale.get_all_ips")
    def test_print_network_info_basic(self, mock_get_ips):
        """Test basic network info print."""
        mock_get_ips.return_value = {"localhost": "127.0.0.1", "all": "0.0.0.0"}

        # Should not raise
        print_network_info()

    @patch("picorouter.tailscale.get_all_ips")
    def test_print_network_info_with_tailscale(self, mock_get_ips):
        """Test network info print with Tailscale."""
        mock_get_ips.return_value = {
            "localhost": "127.0.0.1",
            "all": "0.0.0.0",
            "tailscale": "100.64.0.1",
        }

        # Should not raise
        print_network_info()
