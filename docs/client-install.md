# Client Installation & Setup

## Install

```bash
pip install finger
```

Or from source:

```bash
git clone https://github.com/magnus919/finger.git
cd finger/client
pip install -e .
```

## Configure

### Set a default host

```bash
finger --config --host example.com
```

This saves `example.com` as your default finger server. All subsequent `--set` and `--auth` commands will use it.

### Authenticate a device

```bash
finger --init jasper@example.com
```

This sends an auth code to the email configured on the finger server. The domain is also saved as your default host.

Check your email and run:

```bash
finger --auth <the-code-from-email>
```

Your device key is saved and you're ready to go.

If the server is in dev mode (no SMTP), check the server logs for the token:

```bash
docker logs finger-server-name | grep "Token:"
```

### Set your status

```bash
finger --set "Working on something cool"
```

With TTL:

```bash
finger --set "At lunch" --ttl 1h
```

### Read a status

```bash
finger jasper@example.com
```

If you have a default host configured:

```bash
finger jasper
```

### Read as plain text (no markdown)

```bash
finger jasper@example.com --plain
```

### Testing against a dev server

If your server is running on HTTP (no TLS):

```bash
finger testuser@localhost:8000 --http
finger --set "Status" --http
finger --init testuser@localhost:8000 --http
```

## Config File Location

`~/.finger/config`

```toml
[default]
host = "example.com"
user = "jasper"

[hosts."example.com"]
key = "***..."
```

## Uninstall

```bash
pip uninstall finger
```
