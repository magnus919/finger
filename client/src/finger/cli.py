"""
Finger CLI — main entry point.

Usage:
  finger user@host                  Read a finger status
  finger --set "status"             Set your status
  finger --set "status" --ttl 2h30m
  finger --init user@host           Bootstrap: request auth
  finger --auth <token>             Complete auth
  finger --deauth user@host         Revoke all keys
  finger --status user@host         List keys
  finger --config --show            Show config
  finger --config --key <key>       Manually set API key
  finger --plain                    Read as plain text
  finger --version                  Show version
"""

import argparse
import sys
import json

from . import __version__
from .config import load, save_key, save, get_host_config
from .resolver import resolve_host
from .client import FingerClient
from .render import render
from .ttl import parse_ttl


def _get_client(host: str, use_https: bool = True) -> FingerClient:
    """Get an authenticated client for a host."""
    cfg = get_host_config(host)
    key = cfg.get("key")
    return FingerClient(host, key=key, use_https=use_https)


def cmd_read(args):
    """Read a user's finger status."""
    user, srv_host, domain = resolve_host(args.user_host)
    if not srv_host:
        srv_host = domain

    client = _get_client(srv_host, use_https=not args.http)

    # If the resolved user is empty, use the full user_host specifier
    read_user = user or args.user_host.split("@")[0]

    status_code, body = client.read_status(read_user)

    if status_code == 200:
        if sys.stdout.isatty():
            header = f"{read_user} ({domain})"
            print(header)
            print()
        print(render(body, plain=args.plain))
    elif status_code == 0:
        print(f"finger: {body}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"finger: error ({status_code})", file=sys.stderr)
        sys.exit(1)


def cmd_set(args):
    """Set a finger status."""
    if not args.status:
        # Read from stdin
        args.status = sys.stdin.read().strip()

    if not args.status:
        print("finger: no status provided", file=sys.stderr)
        sys.exit(1)

    # Determine host. Use --user if provided, else from config default
    if args.user:
        user, srv_host, domain = resolve_host(args.user)
    elif args.user_host:
        user, srv_host, domain = resolve_host(args.user_host)
    else:
        cfg = load()
        default_host = cfg.get("default", {}).get("host")
        if not default_host:
            print("finger: no default host configured. Use --user or set in config.", file=sys.stderr)
            sys.exit(1)
        user = cfg.get("default", {}).get("user", "")
        srv_host = default_host
        domain = default_host

    if not srv_host:
        srv_host = domain

    client = _get_client(srv_host, use_https=not args.http)

    if args.user:
        write_user = user or args.user.split("@")[0]
    elif args.user_host:
        write_user = user or args.user_host.split("@")[0]
    else:
        write_user = user or "user"

    status_code, body = client.write_status(write_user, args.status, ttl=args.ttl)

    if status_code == 200:
        print("Status set.")
    else:
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, TypeError):
            detail = body
        print(f"finger: error: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_init(args):
    """Request auth token for a host."""
    user, srv_host, domain = resolve_host(args.user_host)
    if not srv_host:
        srv_host = domain

    client = FingerClient(srv_host, use_https=not args.http)
    status_code, body = client.request_auth()

    if status_code == 200:
        # Save the domain as default host and user for subsequent commands
        cfg = load()
        cfg["default"]["host"] = domain
        if user:
            cfg["default"]["user"] = user
        save(cfg)
        print(f"Auth code sent to the email for {domain}.")
        print("Check your email and run:")
        print(f"  finger --auth <code>")
    else:
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, TypeError):
            detail = body
        print(f"finger: error: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_auth(args):
    """Complete auth with a token."""
    token = args.token

    # Try to find the host from the default config
    cfg = load()
    default_host = cfg.get("default", {}).get("host")
    if not default_host:
        print("finger: no default host configured. Set one with --config or run --init first.", file=sys.stderr)
        sys.exit(1)

    user, srv_host, domain = resolve_host(default_host)
    if not srv_host:
        srv_host = domain

    client = FingerClient(srv_host, use_https=not args.http)
    status_code, body = client.confirm_auth(token)

    if status_code == 200:
        try:
            data = json.loads(body)
            device_key = data.get("device_key")
            if device_key:
                save_key(domain, device_key)
                print(f"Device key saved for {domain}.")
                print("You can now set your status with: finger --set \"Your status here\"")
        except (json.JSONDecodeError, TypeError):
            print(body)
    else:
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, TypeError):
            detail = body
        print(f"finger: error: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_deauth(args):
    """Revoke all device keys."""
    user, srv_host, domain = resolve_host(args.user_host)
    if not srv_host:
        srv_host = domain

    client = _get_client(srv_host, use_https=not args.http)
    status_code, body = client._request("POST", "/.well-known/finger/deauth")

    if status_code == 200:
        print(f"All device keys for {domain} have been revoked.")
        print("Re-authorize with: finger --init")
    else:
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, TypeError):
            detail = body
        print(f"finger: error: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """List active keys."""
    user, srv_host, domain = resolve_host(args.user_host)
    if not srv_host:
        srv_host = domain

    client = _get_client(srv_host, use_https=not args.http)
    status_code, body = client.list_keys()

    if status_code == 200:
        try:
            data = json.loads(body)
            keys = data.get("keys", [])
            if keys:
                print(f"Active keys for {domain}:")
                for k in keys:
                    label = k.get("label") or "unnamed"
                    print(f"  {label}  (last used: {k.get('last_used', 'unknown')})")
            else:
                print(f"No active keys for {domain}.")
        except (json.JSONDecodeError, TypeError):
            print(body)
    else:
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, TypeError):
            detail = body
        print(f"finger: error: {detail}", file=sys.stderr)
        sys.exit(1)


def cmd_config(args):
    """Show or modify config."""
    cfg = load()

    if args.show:
        import pathlib
        config_path = pathlib.Path.home() / ".finger" / "config"
        if config_path.exists():
            print(config_path.read_text().strip())
        else:
            print("No config file found.")
        return

    if args.key:
        # Manually set an API key
        if not cfg.get("default", {}).get("host"):
            print("finger: no default host configured. Set one with: finger --config --host <domain>", file=sys.stderr)
            sys.exit(1)
        save_key(cfg["default"]["host"], args.key)
        print("Key saved.")
        return

    if args.host:
        cfg["default"]["host"] = args.host
        save(cfg)
        print(f"Default host set to {args.host}.")
        return

    if args.user:
        cfg["default"]["user"] = args.user
        save(cfg)
        print(f"Default user set to {args.user}.")
        return


def main():
    parser = argparse.ArgumentParser(
        prog="finger",
        description="Modern finger protocol client (RFC 1288 over HTTPS)",
    )

    # Global flags
    parser.add_argument("--plain", action="store_true", help="Plain text output (no formatting)")
    parser.add_argument("--http", action="store_true", help="Use HTTP instead of HTTPS (dev/testing)")
    parser.add_argument("--version", action="store_true", help="Show version")

    # Subcommands via mutually exclusive groups
    parser.add_argument("--set", dest="status", nargs="?", const=None, default=None,
                        help="Set your finger status")
    parser.add_argument("--ttl", help="TTL for status (e.g., 2h30m, 30m, or ISO datetime)")
    parser.add_argument("--user", help="User@host for write operations (overrides default)")

    parser.add_argument("--init", dest="init_host", nargs="?", const=None, default=None,
                        help="Request auth for a host")
    parser.add_argument("--auth", dest="token", nargs="?", const=None, default=None,
                        help="Complete auth with token")
    parser.add_argument("--deauth", dest="deauth_host", nargs="?", const=None, default=None,
                        help="Revoke all device keys")
    parser.add_argument("--status", dest="status_host", nargs="?", const=None, default=None,
                        help="Show active keys")

    parser.add_argument("--config", action="store_true", help="Config management")
    parser.add_argument("--show", action="store_true", help="Show config (with --config)")
    parser.add_argument("--key", help="Set API key (with --config --key)")
    parser.add_argument("--host", help="Set default host (with --config --host)")

    parser.add_argument("user_host", nargs="?", help="user@host to query")

    args = parser.parse_args()

    if args.version:
        print(f"finger v{__version__}")
        return

    if args.init_host:
        args.user_host = args.init_host
        cmd_init(args)
    elif args.token:
        cmd_auth(args)
    elif args.deauth_host:
        args.user_host = args.deauth_host
        cmd_deauth(args)
    elif args.status_host:
        args.user_host = args.status_host
        cmd_status(args)
    elif args.config:
        cmd_config(args)
    elif args.status is not None:
        cmd_set(args)
    elif args.user_host:
        cmd_read(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
