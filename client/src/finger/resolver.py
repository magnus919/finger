"""
SRV record resolution for finger.

Resolves _finger._tcp.<domain> to find the HTTPS server.
Falls back to <domain> if no SRV record exists.
"""

import socket
import urllib.parse

# Standard DNS port for SRV lookups
DNS_PORT = 53


def resolve_host(user_host: str) -> tuple[str, str, str]:
    """Resolve a finger host.

    Input: "user@host" or "host"
    Returns: (user, srv_host, domain)

    Resolves _finger._tcp.<domain> via SRV record.
    Falls back to direct <domain> if no SRV found.
    """
    if "@" in user_host:
        user, domain = user_host.rsplit("@", 1)
    else:
        user = None
        domain = user_host

    srv_host = _resolve_srv(domain)

    return user or "", srv_host or domain, domain


def _resolve_srv(domain: str) -> str | None:
    """Look up _finger._tcp SRV record. Returns the target hostname or None."""
    try:
        results = socket.getaddrinfo(
            f"_finger._tcp.{domain}",
            0,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP,
        )
        # SRV records aren't returned by getaddrinfo directly in all platforms.
        # Fall back to manual lookup.
    except socket.gaierror:
        pass

    # Try a manual DNS SRV lookup with a simple approach
    # Use the 'host' command if available, or fall back to no SRV
    import subprocess

    try:
        result = subprocess.run(
            ["dig", "+short", "SRV", f"_finger._tcp.{domain}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) >= 4:
                target = parts[3].rstrip(".")
                return target
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try Python's resolver fallback
    try:
        import dns.resolver

        answers = dns.resolver.resolve(f"_finger._tcp.{domain}", "SRV")
        if answers:
            return str(answers[0].target).rstrip(".")
    except ImportError:
        pass
    except Exception:
        pass

    return None


def build_url(host: str, user: str, path: str = "") -> str:
    """Build the HTTPS URL for a finger request."""
    base = f"https://{host}"
    if path:
        base += path
    return base
