"""
HTTP client for finger protocol operations.
"""

import json
import urllib.request
import urllib.parse
import urllib.error


class FingerClient:
    """Make finger protocol requests over HTTPS."""

    def __init__(self, host: str, key: str | None = None, use_https: bool = True):
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}"
        self.key = key

    def _request(
        self,
        method: str,
        path: str,
        data: str | None = None,
        headers: dict | None = None,
    ) -> tuple[int, str]:
        """Make an HTTP request and return (status_code, body)."""
        url = self.base_url + path
        req_headers = {}
        if self.key:
            req_headers["Authorization"] = f"Bearer {self.key}"
        if data is not None:
            req_headers["Content-Type"] = "text/plain"
        if headers:
            req_headers.update(headers)

        body_bytes = data.encode("utf-8") if data else None
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")
        except urllib.error.URLError as e:
            return 0, f"Connection failed: {e.reason}"

    def read_status(self, user: str) -> tuple[int, str]:
        """GET /.well-known/finger?user=<user>"""
        path = f"/.well-known/finger?user={urllib.parse.quote(user)}"
        return self._request("GET", path)

    def write_status(self, user: str, status: str, ttl: str | None = None) -> tuple[int, str]:
        """PUT /.well-known/finger/<user>/plan"""
        path = f"/.well-known/finger/{urllib.parse.quote(user)}/plan"
        if ttl:
            path += f"?ttl={urllib.parse.quote(ttl)}"
        return self._request("PUT", path, data=status)

    def delete_status(self, user: str) -> tuple[int, str]:
        """DELETE /.well-known/finger/<user>/plan"""
        path = f"/.well-known/finger/{urllib.parse.quote(user)}/plan"
        return self._request("DELETE", path)

    def request_auth(self) -> tuple[int, str]:
        """POST /.well-known/finger/request-auth"""
        return self._request("POST", "/.well-known/finger/request-auth")

    def confirm_auth(self, token: str) -> tuple[int, str]:
        """POST /.well-known/finger/confirm-auth"""
        headers = {"Content-Type": "application/json"}
        data = json.dumps({"token": token})
        path = "/.well-known/finger/confirm-auth"
        url = self.base_url + path
        req = urllib.request.Request(
            url,
            data=data.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")
        except urllib.error.URLError as e:
            return 0, f"Connection failed: {e.reason}"

    def list_keys(self) -> tuple[int, str]:
        """GET /.well-known/finger/keys"""
        return self._request("GET", "/.well-known/finger/keys")
