import re
from typing import Any, Dict, List

from utils.helpers import make_finding, summarize_findings


def _contains_phrase(text: str, phrases: List[str]) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in phrases)


def _check_faq(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    text = parsed_page.get("visible_text", "")
    headings = parsed_page.get("headings", {})
    heading_text = " ".join([" ".join(values) for values in headings.values()]).lower()

    has_faq_heading = _contains_phrase(heading_text, ["faq", "frequently asked"])
    qmarks = len(re.findall(r"\?", text))

    if has_faq_heading and qmarks >= 3:
        return make_finding(
            check_id="content_faq",
            status="pass",
            severity="low",
            message="FAQ-like structure detected.",
            details={"question_marks": qmarks, "faq_heading": has_faq_heading},
        )

    return make_finding(
        check_id="content_faq",
        status="info",
        severity="low",
        message="No strong FAQ pattern detected.",
        details={"question_marks": qmarks, "faq_heading": has_faq_heading},
    )


def _check_examples(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    text = parsed_page.get("visible_text", "")
    found = _contains_phrase(
        text,
        ["for example", "example", "use case", "case study", "sample"],
    )

    if found:
        return make_finding(
            check_id="content_examples",
            status="pass",
            severity="low",
            message="Examples or use-cases language detected.",
            details={},
        )

    return make_finding(
        check_id="content_examples",
        status="warning",
        severity="low",
        message="Consider adding examples or use-cases to improve content usefulness.",
        details={},
    )


def _check_content_block(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    text = parsed_page.get("visible_text", "")
    word_count = parsed_page.get("word_count", 0)
    paragraph_like = len([part for part in text.split(".") if len(part.split()) >= 8])

    if word_count >= 300 and paragraph_like >= 3:
        return make_finding(
            check_id="content_content_block",
            status="pass",
            severity="low",
            message="Supporting content blocks look sufficient.",
            details={"word_count": word_count, "paragraph_like_sections": paragraph_like},
        )

    return make_finding(
        check_id="content_content_block",
        status="warning",
        severity="medium",
        message="Supporting content appears limited.",
        details={"word_count": word_count, "paragraph_like_sections": paragraph_like},
    )


def _check_multilanguage(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    hreflang = parsed_page.get("hreflang", [])
    if len(hreflang) >= 2:
        return make_finding(
            check_id="content_multilanguage",
            status="pass",
            severity="low",
            message="Multiple hreflang variants detected.",
            details={"hreflang": hreflang[:10]},
        )

    if len(hreflang) == 1:
        return make_finding(
            check_id="content_multilanguage",
            status="info",
            severity="low",
            message="Single hreflang alternate detected.",
            details={"hreflang": hreflang},
        )

    return make_finding(
        check_id="content_multilanguage",
        status="info",
        severity="low",
        message="No hreflang alternates detected.",
        details={"hreflang": []},
    )


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    findings: List[Dict[str, Any]] = [
        _check_faq(parsed_page),
        _check_examples(parsed_page),
        _check_content_block(parsed_page),
        _check_multilanguage(parsed_page),
    ]

    return {
        "module": "checks.content",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
