from typing import Any, Dict

from utils.parser import parse_html_document


class Extractor:
    def extract(self, crawl_result: Dict[str, Any]) -> Dict[str, Any]:
        fetch_data = crawl_result.get("fetch", {})
        html = fetch_data.get("html", "")
        url = fetch_data.get("final_url") or crawl_result.get("normalized_url") or crawl_result.get("input_url", "")

        if not html:
            return {
                "module": "core.extractor",
                "ok": False,
                "url": url,
                "parsed": parse_html_document("", url),
                "summary": {
                    "error": "no_html_to_parse",
                    "links": 0,
                    "images": 0,
                    "word_count": 0,
                },
            }

        parsed = parse_html_document(html, base_url=url)
        return {
            "module": "core.extractor",
            "ok": parsed.get("parse_error", "") == "",
            "url": url,
            "parsed": parsed,
            "summary": {
                "error": parsed.get("parse_error", ""),
                "title_length": len(parsed.get("title", "")),
                "links": len(parsed.get("links", [])),
                "images": len(parsed.get("images", [])),
                "word_count": parsed.get("word_count", 0),
            },
        }
