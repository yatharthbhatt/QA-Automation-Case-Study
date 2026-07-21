"""
BaseApiClient — shared HTTP behaviour for every API service client.

Owns the cross-cutting concerns so individual clients stay tiny:
- base URL joining
- auth header (Bearer)
- multi-tenant header (X-Tenant-ID)  <-- critical for this platform
- retry with backoff on transient 5xx / connection errors (NOT on 4xx — those are real failures)
- consistent logging
"""
from __future__ import annotations

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from utils.logger import get_logger

log = get_logger("api")

# Retry only on things that are genuinely transient. A 4xx means the test found a real problem
# (or sent a bad request) — retrying would hide bugs, which is the opposite of what we want.
_TRANSIENT = (requests.ConnectionError, requests.Timeout)


class ApiError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        super().__init__(
            f"{response.request.method} {response.request.url} -> {response.status_code}\n{response.text}"
        )


class BaseApiClient:
    def __init__(self, base_url: str, token: str, tenant_id: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": tenant_id,
                "Content-Type": "application/json",
            }
        )

    @retry(
        retry=retry_if_exception_type(_TRANSIENT),
        wait=wait_exponential(multiplier=0.5, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _request(self, method: str, path: str, expected: tuple[int, ...] = (200, 201), **kwargs):
        url = f"{self.base_url}{path}"
        log.info("%s %s", method, url)
        resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        if resp.status_code not in expected:
            raise ApiError(resp)
        return resp

    def get(self, path, expected=(200,), **kw):
        return self._request("GET", path, expected, **kw)

    def post(self, path, expected=(200, 201), **kw):
        return self._request("POST", path, expected, **kw)

    def delete(self, path, expected=(200, 204), **kw):
        return self._request("DELETE", path, expected, **kw)
