"""Minimal HTTP client on urllib with retries and JSON helpers."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

USER_AGENT = "Mozilla/5.0 (compatible; trading-skills/0.1; +https://github.com/reddygopalkrishna/trading-skills)"


class HTTPError(RuntimeError):
    def __init__(self, status: int, message: str, body: str = ""):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


def request(method: str, url: str, params: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
            timeout: float = 20.0, retries: int = 2, backoff: float = 1.5) -> bytes:
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(clean, doseq=True)
    body = None
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = urllib.parse.urlencode({k: v for k, v in data.items() if v is not None}).encode()
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method=method.upper(), headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:2000]
            # retry only on throttling / transient server errors, never on order endpoints' 4xx
            if e.code in (429, 500, 502, 503, 504) and attempt < retries and method.upper() == "GET":
                time.sleep(backoff * (attempt + 1))
                last_err = HTTPError(e.code, e.reason, text)
                continue
            raise HTTPError(e.code, str(e.reason), text) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < retries and method.upper() == "GET":
                time.sleep(backoff * (attempt + 1))
                continue
            raise RuntimeError(f"network error for {urllib.parse.urlsplit(url).netloc}: {e}") from None
    raise RuntimeError(f"request failed: {last_err}")


def get_json(url: str, **kw) -> Any:
    return json.loads(request("GET", url, **kw).decode("utf-8"))
