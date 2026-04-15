from typing import Any, Dict, List


def _area_lines(area_scores: Dict[str, int]) -> List[str]:
    if not area_scores:
        return ["- No area scores available."]
    lines = []
    for area, score in sorted(area_scores.items()):
        lines.append(f"- {area}: {score}/100")
    return lines


def _top_actions(recommendations: List[Dict[str, Any]]) -> List[str]:
    if not recommendations:
        return ["- No actions generated."]
    return [
        f"- P{item.get('priority')}: {item.get('action')}"
        for item in recommendations[:5]
    ]


def run(
    analysis_result: Dict[str, Any],
    score_result: Dict[str, Any],
    suggestions_result: Dict[str, Any],
    config: Any,
) -> Dict[str, Any]:
    url = analysis_result.get("url", "")
    overall = score_result.get("overall_score", 0)
    grade = score_result.get("grade", "N/A")
    area_scores = score_result.get("area_scores", {})
    recommendations = suggestions_result.get("recommendations", [])

    if overall >= 85:
        posture = "strong overall SEO health"
    elif overall >= 70:
        posture = "good baseline with clear optimization opportunities"
    elif overall >= 55:
        posture = "moderate performance with meaningful issues to address"
    else:
        posture = "high-risk SEO posture requiring prioritized fixes"

    sections = {
        "executive_summary": (
            f"Audit target: {url}\n"
            f"Overall score: {overall}/100 (grade {grade}).\n"
            f"This site currently shows {posture}."
        ),
        "area_scores": "\n".join(_area_lines(area_scores)),
        "priority_actions": "\n".join(_top_actions(recommendations)),
        "method": (
            "This report is based on deterministic Python checks for crawlability, on-page, "
            "performance, structured data, content, and indexing. AI layers summarize and prioritize "
            "actions using compact findings only."
        ),
    }

    return {
        "module": "ai.report_writer",
        "report_title": "SEO Audit Report",
        "url": url,
        "sections": sections,
        "text": "\n\n".join([
            "SEO AUDIT REPORT",
            sections["executive_summary"],
            "Area Scores:\n" + sections["area_scores"],
            "Priority Actions:\n" + sections["priority_actions"],
            "Method:\n" + sections["method"],
        ]),
    }
