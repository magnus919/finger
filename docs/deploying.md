# Deploying a Finger Server

## Quick Deploy (Docker)

The server runs as a single-user Docker container. Each user gets their own container.

```bash
docker run -d --name finger-jasper \
  -e FINGER_USER=jasper \
  -e FINGER_USER_EMAIL=jasper@example.com \
  -e FINGER_EMAIL_FROM=finger@example.com \
  -p 8000:8000 \
  finger-server:latest
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FINGER_USER` | Yes | — | The username this container serves |
| `FINGER_USER_EMAIL` | No | — | Email address for auth magic links |
| `FINGER_EMAIL_FROM` | No | `finger@localhost` | From address for auth emails |
| `FINGER_PLANS_DIR` | No | `/data/plans` | Where plan files are stored |
| `FINGER_KEYS_PATH` | No | `/data/keys.json` | Where device keys are stored |
| `FINGER_TOKEN_DIR` | No | `/data/auth_tokens` | Where one-time auth tokens are stored |
| `SMTP_HOST` | For email | — | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | For auth | — | SMTP username |
| `SMTP_PASS` | For auth | — | SMTP password |

## SMTP Configuration (Required for Auth)

The auth flow sends magic links via email. Without SMTP, the server logs tokens to stdout (dev mode only).

```bash
docker run -d --name finger-jasper \
  -e FINGER_USER=jasper \
  -e FINGER_USER_EMAIL=jasper@example.com \
  -e FINGER_EMAIL_FROM=finger@example.com \
  -e SMTP_HOST=smtp.mailgun.org \
  -e SMTP_PORT=587 \
  -e SMTP_USER=postmaster@mg.example.com \
  -e SMTP_PASS=your-smtp-password \
  finger-server:latest
```

## Persistence

Plan files and keys are stored in `/data/`. Mount a volume to persist across container replacements:

```bash
docker run -d --name finger-jasper \
  -v finger-data:/data \
  ... finger-server:latest
```

## With Docker Compose

```yaml
services:
  finger:
    build: ./server
    container_name: finger-jasper
    environment:
      - FINGER_USER=jasper
      - FINGER_USER_EMAIL=jasper@example.com
      - FINGER_EMAIL_FROM=finger@example.com
      - SMTP_HOST=$$
      - SMTP_PORT=587
      - SMTP_USER=$$
      - SMTP_PASS=$$
    volumes:
      - finger_data:/data
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  finger_data:
```

Copy `.env.example` to `.env` and fill in your values.

## DNS SRV Record

To use `finger user@yourdomain.com`, add an SRV record:

```
_finger._tcp.yourdomain.com. 3600 IN SRV 0 1 443 finger.yourdomain.com.
```

This tells the client to connect to `finger.yourdomain.com:443` via HTTPS.

If no SRV record exists, the client falls back to:
```
https://yourdomain.com/.well-known/finger?user=<user>
```

## TLS / Reverse Proxy

The server runs on port 8000 internally. Put Traefik, nginx, or Caddy in front for TLS.

**Traefik example:**
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.finger.rule=Host(`finger.example.com`)"
  - "traefik.http.routers.finger.tls=true"
  - "traefik.http.routers.finger.tls.certresolver=letsencrypt"
  - "traefik.http.services.finger.loadbalancer.server.port=8000"
```

## Health Check

```bash
curl https://finger.example.com/health
# {"status":"ok"}
```

## Testing Without TLS (Dev Mode)

Run on localhost and use the `--http` flag:

```bash
finger testuser@localhost:8000 --http
finger --init testuser@localhost:8000 --http
```
