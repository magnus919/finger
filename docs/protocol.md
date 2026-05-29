# Finger Protocol Specification

## Overview

finger is a modern implementation of the Finger User Information Protocol (RFC 1288) transported over HTTPS. It retains the same CLI semantics while replacing raw TCP with modern authentication, encryption, and DNS-based service discovery.

## Service Discovery

The client resolves the finger service for a domain via an SRV record:

```
_finger._tcp.<domain>  IN  SRV  <priority> <weight> <port> <target>
```

### SRV Record Example

```
_finger._tcp.example.com.  3600  IN  SRV  0  1  443  finger-srv.internal.example.com.
```

This directs the client to `https://finger-srv.internal.example.com:443`.

### Fallback

If no SRV record is found, the client falls back to the direct domain:

```
https://<domain>/.well-known/finger?user=<user>
```

## Endpoints

### Read a User's Status

```
GET /.well-known/finger?user=<username>
```

**Response (status exists):**
```
Content-Type: text/plain; charset=utf-8

Sitting on my porch. The frogs are loud tonight.
```

Format: plain text, optionally markdown. The client decides whether to render markdown or strip it.

**Response (no status):**
```
Content-Type: text/plain; charset=utf-8

-
```

A single `-` indicates the user has no current status or the status has expired.

**Response (no user parameter):**

`303 See Other` redirect to the root URL of the server.

### Stream

This endpoint is public and requires no authentication.

### Set a User's Status

```
PUT /.well-known/finger/<username>/plan

Authorization: Bearer <device-key>
Content-Type: text/plain

Your status text here, optionally with **markdown**.
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ttl` | string | Optional time-to-live. See TTL format below. |

**Response:**
```json
{"status": "ok", "user": "jasper", "expires_at": 1717000000}
```

`expires_at` is `null` if no TTL was set, or a unix timestamp if a TTL was specified.

### Clear a User's Status

```
DELETE /.well-known/finger/<username>/plan
Authorization: Bearer <device-key>
```

### Request Auth Token

```
POST /.well-known/finger/request-auth
```

Triggers an email to the configured user with a one-time auth code. In dev mode (no SMTP), the token is logged to stdout.

### Confirm Auth

```
POST /.well-known/finger/confirm-auth
Content-Type: application/json

{"token": "<one-time-token>"}
```

**Response:**
```json
{"status": "ok", "device_key": "sk-finger-<64-hex-chars>"}
```

The device key is a long-lived credential. Store it and use it for all subsequent write operations.

### Deauthorize All Keys

```
POST /.well-known/finger/deauth
```

Revokes all device keys. After this, each device must re-authenticate.

### List Active Keys

```
GET /.well-known/finger/keys
Authorization: Bearer <device-key>
```

**Response:**
```json
{
  "status": "ok",
  "keys": [
    {"prefix": "sk-finger-a1b2...", "created_at": 1717000000, "last_used": 1717000100, "label": null}
  ]
}
```

## TTL Format

TTL values can be specified as a duration or an absolute datetime.

### Duration

```
finger --set "Status" --ttl 30m     # 30 minutes
finger --set "Status" --ttl 2h30m   # 2 hours 30 minutes
finger --set "Status" --ttl 1d      # 1 day
finger --set "Status" --ttl 45s     # 45 seconds
```

Components: days (`d`), hours (`h`), minutes (`m`), seconds (`s`). Any combination works.

### Absolute Datetime

```
finger --set "Status" --ttl "2026-06-01T12:00:00Z"
finger --set "Status" --ttl "2026-06-01 12:00:00"
```

ISO 8601 format. Supports `Z` suffix and space-separated datetime.

### No TTL Means Indefinite

If no TTL is specified, the status lasts until explicitly replaced or deleted.

## Expiry

TTL expiry is checked lazily:

1. On every read request, the server compares the stored `expires_at` timestamp against the current time
2. If expired, both the plan file (`.md`) and metadata file (`.meta`) are deleted atomically
3. On container startup, all `.meta` files are scanned and expired entries are cleaned up

This means expired statuses are removed at most one boot cycle after they expire, regardless of whether anyone reads them.

## Authentication Model

The server uses pre-shared device keys for write access:

1. User requests auth via email magic link
2. Server emails a one-time token (15-minute expiry)
3. User presents the token to receive a long-lived device key
4. The device key is sent as `Authorization: Bearer <key>` on write requests
5. Keys are stored as SHA-256 hashes on the server
6. Deauth-all rotates the trust root, invalidating all existing keys

Read access is always public. There is no user enumeration.

## Storage Layout

```
/data/
├── plans/
│   ├── jasper.md          # Status content (markdown text)
│   ├── jasper.meta        # {"expires_at": 1717000000|null}
│   └── ...
├── keys.json              # Device key store (SHA-256 hashed)
└── auth_tokens/           # One-time auth tokens (auto-expired)
    └── <hex-token>        # {"expires_at": ...}
```

## Client Configuration

The client stores config at `~/.finger/config` in TOML format:

```toml
[default]
host = "example.com"
user = "jasper"

[hosts."example.com"]
key = "sk-finger-a1b2c3..."
```
