"""
Client configuration management.

Config stored in ~/.finger/config as TOML.

[default]
host = "example.com"

[hosts."example.com"]
key = "sk-finger-..."
"""

import os
import pathlib

_CONFIG_DIR = pathlib.Path.home() / ".finger"
_CONFIG_FILE = _CONFIG_DIR / "config"


def _ensure_dir():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load config. Returns dict with 'default' and 'hosts' keys."""
    config = {"default": {}, "hosts": {}}
    if not _CONFIG_FILE.exists():
        return config

    current_section = None
    current_host = None

    for line in _CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1]
            if name == "default":
                current_section = "default"
                current_host = None
            elif name.startswith('hosts."') and name.endswith('"'):
                current_section = "hosts"
                current_host = name[7:-1]  # Strip 'hosts."' prefix and trailing '"'
                if current_host not in config["hosts"]:
                    config["hosts"][current_host] = {}
            else:
                current_section = None
                current_host = None
        elif "=" in line and current_section:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"')
            if current_section == "default":
                config["default"][key] = val
            elif current_host:
                config["hosts"][current_host][key] = val

    return config


def save(cfg: dict):
    """Save config to ~/.finger/config."""
    _ensure_dir()
    lines = []

    if cfg.get("default"):
        lines.append("[default]")
        for k, v in cfg["default"].items():
            lines.append(f'{k} = "{v}"')
        lines.append("")

    if cfg.get("hosts"):
        for host, opts in cfg["hosts"].items():
            if host == "default":
                continue
            lines.append(f'[hosts."{host}"]')
            for k, v in opts.items():
                lines.append(f'{k} = "{v}"')
            lines.append("")

    _CONFIG_FILE.write_text("\n".join(lines).strip() + "\n")


def get_host_config(host: str) -> dict:
    """Get config for a specific host, merged with defaults."""
    cfg = load()
    result = dict(cfg.get("default", {}))
    if host in cfg.get("hosts", {}):
        result.update(cfg["hosts"][host])
    return result


def save_key(host: str, key: str):
    """Save a device key for a host."""
    cfg = load()
    if "hosts" not in cfg:
        cfg["hosts"] = {}
    if host not in cfg["hosts"]:
        cfg["hosts"][host] = {}
    cfg["hosts"][host]["key"] = key
    save(cfg)
