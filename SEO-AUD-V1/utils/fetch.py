import time
from typing import Any, Dict

import requests


class FetchClient:
    def __init__(self, config: Any) -> None:
        self.timeout = int(getattr(config, "request_timeout", 15))
        self.retries = int(getattr(config, "request_retries", 2))
        self.backoff = float(getattr(config, "retry_backoff_seconds", 1.0))
        user_agent = getattr(config, "user_agent", "SEO-AUD-V1/1.0")

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _build_result(
        self,
        requested_url: str,
        *,
        final_url: str = "",
        status_code: int = 0,
        reason: str = "",
        headers: Dict[str, str] | None = None,
        html: str = "",
        elapsed_ms: int = 0,
        attempts: int = 1,
        error: str = "",
    ) -> Dict[str, Any]:
        return {
            "requested_url": requested_url,
            "final_url": final_url or requested_url,
            "status_code": status_code,
            "reason": reason,
            "headers": headers or {},
            "html": html,
            "elapsed_ms": elapsed_ms,
            "attempts": attempts,
            "redirected": final_url != requested_url if final_url else False,
            "error": error,
        }

    def fetch(self, url: str, method: str = "GET", allow_redirects: bool = True) -> Dict[str, Any]:
        last_error = ""

        for attempt in range(1, self.retries + 2):
            started = time.perf_counter()
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    allow_redirects=allow_redirects,
                )
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                headers = {k.lower(): v for k, v in response.headers.items()}
                return self._build_result(
                    requested_url=url,
                    final_url=response.url,
                    status_code=response.status_code,
                    reason=response.reason,
                    headers=headers,
                    html=response.text if method.upper() != "HEAD" else "",
                    elapsed_ms=elapsed_ms,
                    attempts=attempt,
                    error="",
                )
            except requests.RequestException as exc:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt <= self.retries:
                    time.sleep(self.backoff * attempt)
                    continue
                return self._build_result(
                    requested_url=url,
                    status_code=0,
                    reason="request_failed",
                    headers={},
                    html="",
                    elapsed_ms=elapsed_ms,
                    attempts=attempt,
                    error=last_error,
                )

        return self._build_result(requested_url=url, error=last_error or "unknown_fetch_error")

    def fetch_status(self, url: str) -> Dict[str, Any]:
        head_result = self.fetch(url=url, method="HEAD", allow_redirects=True)
        if head_result.get("status_code", 0) >= 400 or head_result.get("status_code", 0) == 0:
            return self.fetch(url=url, method="GET", allow_redirects=True)
        return head_result

    def close(self) -> None:
        self.session.close()
