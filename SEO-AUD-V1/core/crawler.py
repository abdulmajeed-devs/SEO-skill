from typing import Any, Dict

from utils.fetch import FetchClient
from utils.urls import normalize_url


class Crawler:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.fetch_client = FetchClient(config)

    def fetch(self, input_url: str) -> Dict[str, Any]:
        normalized_url = normalize_url(input_url)
        if not normalized_url:
            return {
                "module": "core.crawler",
                "ok": False,
                "input_url": input_url,
                "normalized_url": "",
                "fetch": {
                    "requested_url": input_url,
                    "final_url": input_url,
                    "status_code": 0,
                    "error": "invalid_url",
                    "html": "",
                },
            }

        fetch_result = self.fetch_client.fetch(normalized_url)
        return {
            "module": "core.crawler",
            "ok": fetch_result.get("error", "") == "",
            "input_url": input_url,
            "normalized_url": normalized_url,
            "fetch": fetch_result,
        }

    def close(self) -> None:
        self.fetch_client.close()
