from typing import Any, Dict, List

from utils.helpers import make_finding, summarize_findings


def _check_jsonld(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    blocks = parsed_page.get("jsonld", [])
    if not blocks:
        return make_finding(
            check_id="structured_jsonld",
            status="warning",
            severity="medium",
            message="No JSON-LD structured data found.",
            details={"count": 0},
        )

    invalid_count = len([item for item in blocks if not item.get("valid")])
    types: List[str] = []
    for item in blocks:
        types.extend(item.get("types", []))

    if invalid_count == 0:
        return make_finding(
            check_id="structured_jsonld",
            status="pass",
            severity="low",
            message="JSON-LD blocks found and parsed successfully.",
            details={"count": len(blocks), "types": sorted(set(types))},
        )

    return make_finding(
        check_id="structured_jsonld",
        status="warning",
        severity="medium",
        message="Some JSON-LD blocks are malformed.",
        details={"count": len(blocks), "invalid_count": invalid_count, "types": sorted(set(types))},
    )


def _check_breadcrumb(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    blocks = parsed_page.get("jsonld", [])
    breadcrumb_blocks = [item for item in blocks if "BreadcrumbList" in item.get("types", [])]

    if not breadcrumb_blocks:
        return make_finding(
            check_id="structured_breadcrumb",
            status="warning",
            severity="low",
            message="BreadcrumbList schema not found.",
            details={},
        )

    valid = 0
    for block in breadcrumb_blocks:
        data = block.get("data", {})
        items = data.get("itemListElement", []) if isinstance(data, dict) else []
        if isinstance(items, list) and len(items) > 0:
            valid += 1

    if valid > 0:
        return make_finding(
            check_id="structured_breadcrumb",
            status="pass",
            severity="low",
            message="Breadcrumb schema detected with item list.",
            details={"breadcrumb_blocks": len(breadcrumb_blocks), "valid_blocks": valid},
        )

    return make_finding(
        check_id="structured_breadcrumb",
        status="warning",
        severity="medium",
        message="Breadcrumb schema found but item list looks incomplete.",
        details={"breadcrumb_blocks": len(breadcrumb_blocks), "valid_blocks": valid},
    )


def _check_opengraph(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    meta = parsed_page.get("meta_tags", {})
    required = ["og:title", "og:description", "og:image", "og:url"]
    missing = [field for field in required if not meta.get(field)]

    if not missing:
        return make_finding(
            check_id="structured_opengraph",
            status="pass",
            severity="low",
            message="Open Graph metadata is complete.",
            details={"required": required},
        )

    return make_finding(
        check_id="structured_opengraph",
        status="warning",
        severity="medium",
        message="Open Graph metadata is missing required tags.",
        details={"missing": missing, "required": required},
    )


def _check_twitter(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    meta = parsed_page.get("meta_tags", {})
    required = ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]
    missing = [field for field in required if not meta.get(field)]

    if not missing:
        return make_finding(
            check_id="structured_twitter",
            status="pass",
            severity="low",
            message="Twitter card metadata is complete.",
            details={"required": required},
        )

    return make_finding(
        check_id="structured_twitter",
        status="warning",
        severity="medium",
        message="Twitter card metadata is missing required tags.",
        details={"missing": missing, "required": required},
    )


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    findings: List[Dict[str, Any]] = [
        _check_jsonld(parsed_page),
        _check_breadcrumb(parsed_page),
        _check_opengraph(parsed_page),
        _check_twitter(parsed_page),
    ]

    return {
        "module": "checks.structured",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
