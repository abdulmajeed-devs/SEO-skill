from typing import Any, Dict, List

from utils.helpers import make_finding, summarize_findings


def _check_indexable(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    meta = parsed_page.get("meta_tags", {})
    robots_meta = (meta.get("robots") or "").lower()
    x_robots = (crawl_result.get("fetch", {}).get("headers", {}).get("x-robots-tag") or "").lower()

    blockers = []
    if "noindex" in robots_meta:
        blockers.append("meta_robots_noindex")
    if "noindex" in x_robots:
        blockers.append("x_robots_noindex")

    robots_signal = context.get("technical_signals", {}).get("robots_disallow_all", False)
    if robots_signal:
        blockers.append("robots_txt_disallow_all")

    if not blockers:
        return make_finding(
            check_id="indexing_indexable",
            status="pass",
            severity="low",
            message="No direct noindex blockers detected.",
            details={"meta_robots": robots_meta, "x_robots": x_robots},
        )

    return make_finding(
        check_id="indexing_indexable",
        status="fail",
        severity="critical",
        message="Indexability blockers detected.",
        details={"blockers": blockers, "meta_robots": robots_meta, "x_robots": x_robots},
    )


def _check_pagination(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    rel_links = parsed_page.get("rel_links", {})
    has_next = bool(rel_links.get("next"))
    has_prev = bool(rel_links.get("prev"))

    if has_next or has_prev:
        return make_finding(
            check_id="indexing_pagination",
            status="pass",
            severity="low",
            message="Pagination signals detected.",
            details={"rel_links": rel_links},
        )

    links = parsed_page.get("links", [])
    numeric_anchor_count = 0
    for link in links:
        text = (link.get("text") or "").strip()
        if text.isdigit() and len(text) <= 3:
            numeric_anchor_count += 1

    if numeric_anchor_count >= 2:
        return make_finding(
            check_id="indexing_pagination",
            status="info",
            severity="low",
            message="Possible pagination links found by numeric anchors.",
            details={"numeric_anchor_count": numeric_anchor_count},
        )

    return make_finding(
        check_id="indexing_pagination",
        status="info",
        severity="low",
        message="No strong pagination signals detected.",
        details={"numeric_anchor_count": numeric_anchor_count},
    )


def _check_thin_content(parsed_page: Dict[str, Any], config: Any) -> Dict[str, Any]:
    words = int(parsed_page.get("word_count", 0))
    threshold = int(getattr(config, "thin_content_word_threshold", 300))

    if words >= threshold:
        return make_finding(
            check_id="indexing_thin_content",
            status="pass",
            severity="low",
            message="Content length is above thin-content threshold.",
            details={"word_count": words, "threshold": threshold},
        )

    if words >= max(120, int(threshold * 0.5)):
        return make_finding(
            check_id="indexing_thin_content",
            status="warning",
            severity="medium",
            message="Content is below recommended threshold and may be thin.",
            details={"word_count": words, "threshold": threshold},
        )

    return make_finding(
        check_id="indexing_thin_content",
        status="fail",
        severity="high",
        message="Content appears very thin.",
        details={"word_count": words, "threshold": threshold},
    )


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    config = context.get("config")
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    findings: List[Dict[str, Any]] = [
        _check_indexable(parsed_page=parsed_page, crawl_result=crawl_result, context=context),
        _check_pagination(parsed_page),
        _check_thin_content(parsed_page, config),
    ]

    return {
        "module": "checks.indexing",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
