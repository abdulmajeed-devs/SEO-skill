from typing import Any, Dict, List


def _message_for_check(check_id: str) -> str:
    mapping = {
        "technical_robots_disallow_all": "Update robots.txt to avoid global disallow for production pages.",
        "technical_https": "Force HTTPS at server level and update canonical/internal links to HTTPS.",
        "technical_broken_links": "Fix broken URLs and add monitoring for link health checks.",
        "onpage_title": "Write concise, unique title tags within target length.",
        "onpage_meta_description": "Add compelling meta descriptions in recommended length range.",
        "onpage_headings": "Ensure one clear H1 and logical heading level progression.",
        "onpage_alt_text": "Add descriptive alt text for informative images.",
        "performance_pagespeed": "Optimize render path, script loading, and image compression for better speed.",
        "performance_caching": "Set cache-control, ETag, and expiration headers for static assets.",
        "structured_jsonld": "Add valid JSON-LD schema matching page intent.",
        "structured_opengraph": "Complete Open Graph tags for better social sharing previews.",
        "structured_twitter": "Complete Twitter card metadata for richer previews.",
        "indexing_indexable": "Remove noindex blockers where indexing is intended.",
        "indexing_thin_content": "Expand content depth with useful explanatory sections.",
    }
    return mapping.get(check_id, "Review this check and apply a targeted SEO improvement.")


def run(analysis_result: Dict[str, Any], score_result: Dict[str, Any], config: Any) -> Dict[str, Any]:
    findings = analysis_result.get("findings", [])
    weak = [item for item in findings if item.get("status") in {"fail", "warning"}]

    prioritized = sorted(
        weak,
        key=lambda item: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item.get("severity", "low"), 3),
            {"fail": 0, "warning": 1}.get(item.get("status", "warning"), 1),
        ),
    )

    recommendations: List[Dict[str, Any]] = []
    seen = set()
    for finding in prioritized:
        check_id = finding.get("check_id", "unknown_check")
        if check_id in seen:
            continue
        seen.add(check_id)
        recommendations.append(
            {
                "priority": len(recommendations) + 1,
                "check_id": check_id,
                "severity": finding.get("severity", "low"),
                "issue": finding.get("message", ""),
                "action": _message_for_check(check_id),
                "module": finding.get("module", ""),
            }
        )
        if len(recommendations) >= 10:
            break

    if not recommendations:
        recommendations.append(
            {
                "priority": 1,
                "check_id": "all_clear",
                "severity": "low",
                "issue": "No failing or warning checks were found.",
                "action": "Maintain current SEO baseline and monitor periodically.",
                "module": "summary",
            }
        )

    return {
        "module": "ai.suggestions",
        "input_score": score_result.get("overall_score", 0),
        "recommendations": recommendations,
        "note": "Generated from weak checks only to avoid repeating raw data.",
    }
