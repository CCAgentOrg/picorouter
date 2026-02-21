"""PicoRouter - Tailscale integration."""

import os
import socket
import subprocess
import re
from typing import Optional, Dict


def get_tailscale_ip() -> Optional[str]:
    """Get Tailscale IP address (100.x.x.x)."""
    try:
        # Method 1: Check Tailscale status
        result = subprocess.run(
            ["tailscale", "status", "--json"], capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            # Find our own Tailscale IP
            for ip, info in data.get("Peer", {}).items():
                if ip.startswith("100."):
                    return ip

            # Check Self
            self_info = data.get("Self", {})
            if "TailscaleIPs" in self_info:
                return self_info["TailscaleIPs"][0]

    except Exception:
        pass

    # Method 2: Parse tailscale ip
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            ip = result.stdout.strip()
            if ip.startswith("100."):
                return ip
    except Exception:
        pass

    return None


def get_all_ips() -> Dict:
    """Get all available network IPs."""
    ips = {
        "localhost": "127.0.0.1",
        "all": "0.0.0.0",
    }

    # Get Tailscale IP
    ts_ip = get_tailscale_ip()
    if ts_ip:
        ips["tailscale"] = ts_ip

    # Get regular network IPs
    try:
        hostname = socket.gethostname()
        # Try to get all addresses
        for addr in socket.getaddrinfo(hostname, None):
            ip = addr[4][0]
            if ":" in ip:  # Skip IPv6
                continue
            if ip.startswith("127."):
                continue
            if ip.startswith("169.254."):  # Link-local
                continue
            if not ips.get("lan"):  # First non-local is LAN
                ips["lan"] = ip
    except Exception:
        pass

    return ips


def is_tailscale_running() -> bool:
    """Check if Tailscale is running."""
    try:
        result = subprocess.run(["tailscale", "status"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def print_network_info():
    """Print available network options."""
    print("\n🌐 Network Options:")
    print("  localhost     127.0.0.1   (local only)")
    print("  all           0.0.0.0      (all interfaces)")

    ips = get_all_ips()

    if "tailscale" in ips:
        print(f"  tailscale    {ips['tailscale']}  (Tailscale VPN)")

    if "lan" in ips:
        print(f"  lan          {ips['lan']}    (local network)")

    if is_tailscale_running():
        print("\n  ✓ Tailscale is running")
    else:
        print("\n  ✗ Tailscale not detected")

    print()


# CLI argument for --host to suggest Tailscale
TAILSCALE_HOST_DOC = """
Host options:
  localhost     Bind to 127.0.0.1 (local only)
  all           Bind to 0.0.0.0 (all interfaces)  
  tailscale     Bind to Tailscale IP (if available)
  lan           Bind to LAN IP (if available)
  Or specify IP directly: 192.168.1.100

Examples:
  python picorouter.py serve                    # All interfaces
  python picorouter.py serve --host localhost   # Local only
  python picorouter.py serve --host tailscale   # Over Tailscale VPN
"""
