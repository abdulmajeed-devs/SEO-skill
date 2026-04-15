import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from utils.helpers import make_finding, summarize_findings


def _check_title(parsed_page: Dict[str, Any], config: Any) -> Dict[str, Any]:
    title = parsed_page.get("title", "")
    min_len = int(getattr(config, "title_min_length", 30))
    max_len = int(getattr(config, "title_max_length", 65))

    if not title:
        return make_finding(
            check_id="onpage_title",
            status="fail",
            severity="high",
            message="Title tag is missing.",
            details={"length": 0, "recommended": f"{min_len}-{max_len}"},
        )

    title_len = len(title)
    if min_len <= title_len <= max_len:
        return make_finding(
            check_id="onpage_title",
            status="pass",
            severity="low",
            message="Title tag exists and length is in recommended range.",
            details={"length": title_len, "title": title},
        )

    return make_finding(
        check_id="onpage_title",
        status="warning",
        severity="medium",
        message="Title length is outside recommended range.",
        details={"length": title_len, "recommended": f"{min_len}-{max_len}", "title": title},
    )


def _check_meta_description(parsed_page: Dict[str, Any], config: Any) -> Dict[str, Any]:
    meta_tags = parsed_page.get("meta_tags", {})
    description = meta_tags.get("description", "")
    min_len = int(getattr(config, "meta_desc_min_length", 120))
    max_len = int(getattr(config, "meta_desc_max_length", 160))

    if not description:
        return make_finding(
            check_id="onpage_meta_description",
            status="fail",
            severity="high",
            message="Meta description is missing.",
            details={"length": 0, "recommended": f"{min_len}-{max_len}"},
        )

    description_len = len(description)
    if min_len <= description_len <= max_len:
        return make_finding(
            check_id="onpage_meta_description",
            status="pass",
            severity="low",
            message="Meta description exists and length is in recommended range.",
            details={"length": description_len},
        )

    return make_finding(
        check_id="onpage_meta_description",
        status="warning",
        severity="medium",
        message="Meta description length is outside recommended range.",
        details={"length": description_len, "recommended": f"{min_len}-{max_len}"},
    )


def _check_headings(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    headings = parsed_page.get("headings", {})
    h1_count = len(headings.get("h1", []))

    present_levels = []
    for level in range(1, 7):
        if headings.get(f"h{level}"):
            present_levels.append(level)

    skipped_level = False
    for idx in range(1, len(present_levels)):
        if present_levels[idx] - present_levels[idx - 1] > 1:
            skipped_level = True
            break

    if h1_count == 1 and not skipped_level:
        return make_finding(
            check_id="onpage_headings",
            status="pass",
            severity="low",
            message="Heading structure appears logical.",
            details={"h1_count": h1_count, "levels": present_levels},
        )

    severity = "high" if h1_count == 0 else "medium"
    return make_finding(
        check_id="onpage_headings",
        status="warning",
        severity=severity,
        message="Heading structure needs improvement.",
        details={"h1_count": h1_count, "levels": present_levels, "skipped_levels": skipped_level},
    )


def _check_alt_text(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    images = parsed_page.get("images", [])
    if not images:
        return make_finding(
            check_id="onpage_alt_text",
            status="info",
            severity="low",
            message="No images found on page.",
            details={"images": 0},
        )

    with_alt = len([img for img in images if img.get("alt", "").strip()])
    ratio = with_alt / len(images)

    if ratio >= 0.9:
        return make_finding(
            check_id="onpage_alt_text",
            status="pass",
            severity="low",
            message="Image alt text coverage is strong.",
            details={"images": len(images), "with_alt": with_alt, "coverage": round(ratio, 2)},
        )

    return make_finding(
        check_id="onpage_alt_text",
        status="warning",
        severity="medium",
        message="Some images are missing descriptive alt text.",
        details={"images": len(images), "with_alt": with_alt, "coverage": round(ratio, 2)},
    )


def _check_internal_links(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    links = parsed_page.get("links", [])
    internal = [link for link in links if link.get("is_internal")]
    unique_internal = len({link.get("url") for link in internal if link.get("url")})

    if unique_internal >= 3:
        return make_finding(
            check_id="onpage_internal_links",
            status="pass",
            severity="low",
            message="Internal linking depth looks healthy for this page.",
            details={"internal_links": len(internal), "unique_destinations": unique_internal},
        )

    return make_finding(
        check_id="onpage_internal_links",
        status="warning",
        severity="medium",
        message="Internal linking could be improved.",
        details={"internal_links": len(internal), "unique_destinations": unique_internal},
    )


def _check_url_keyword(current_url: str, target_keyword: str) -> Dict[str, Any]:
    if not target_keyword.strip():
        return make_finding(
            check_id="onpage_url_keyword",
            status="info",
            severity="low",
            message="Keyword not provided. URL keyword check skipped.",
            details={},
        )

    slug = urlparse(current_url).path.lower()
    terms = [token for token in re.split(r"[^a-z0-9]+", target_keyword.lower()) if token]
    missing_terms = [term for term in terms if term not in slug]

    if not missing_terms:
        return make_finding(
            check_id="onpage_url_keyword",
            status="pass",
            severity="low",
            message="Target keyword terms appear in URL slug.",
            details={"keyword": target_keyword, "slug": slug},
        )

    return make_finding(
        check_id="onpage_url_keyword",
        status="warning",
        severity="medium",
        message="Some target keyword terms are missing from URL slug.",
        details={"keyword": target_keyword, "missing_terms": missing_terms, "slug": slug},
    )


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    config = context.get("config")
    target_keyword = context.get("target_keyword", "")
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    findings: List[Dict[str, Any]] = [
        _check_title(parsed_page, config),
        _check_meta_description(parsed_page, config),
        _check_headings(parsed_page),
        _check_alt_text(parsed_page),
        _check_internal_links(parsed_page),
        _check_url_keyword(current_url=current_url, target_keyword=target_keyword),
    ]

    return {
        "module": "checks.onpage",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
