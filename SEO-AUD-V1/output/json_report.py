import json
import os
from typing import Any, Dict
from urllib.parse import urlparse

from utils.helpers import safe_filename, utc_now_iso


def run(final_audit: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)

    url = final_audit.get("url", "unknown")
    host = urlparse(url).netloc or "unknown-host"
    timestamp = utc_now_iso().replace(":", "").replace("+00:00", "Z")
    file_name = f"{safe_filename(host)}_{safe_filename(timestamp)}.json"
    path = os.path.join(output_dir, file_name)

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(final_audit, handle, indent=2, ensure_ascii=True)

    return {
        "module": "output.json_report",
        "status": "ok",
        "url": url,
        "path": path,
    }
