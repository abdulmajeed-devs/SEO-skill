from typing import Any, Dict, List


def _weight_for_finding(status: str, severity: str) -> float:
    status_weight = {
        "fail": 1.0,
        "warning": 0.6,
        "pass": 0.0,
        "info": 0.2,
    }.get(status, 0.2)

    severity_weight = {
        "critical": 3.0,
        "high": 2.0,
        "medium": 1.0,
        "low": 0.5,
    }.get(severity, 0.5)

    return status_weight * severity_weight


def _score_from_findings(findings: List[Dict[str, Any]]) -> int:
    penalty = 0.0
    for finding in findings:
        penalty += _weight_for_finding(
            status=finding.get("status", "info"),
            severity=finding.get("severity", "low"),
        )

    score = max(0.0, 100.0 - (penalty * 2.8))
    return int(round(score))


def run(analysis_result: Dict[str, Any], config: Any) -> Dict[str, Any]:
    modules = analysis_result.get("modules", {})
    area_scores: Dict[str, int] = {}

    for area_name, area_result in modules.items():
        area_findings = area_result.get("findings", [])
        area_scores[area_name] = _score_from_findings(area_findings)

    if area_scores:
        overall = int(round(sum(area_scores.values()) / len(area_scores)))
    else:
        overall = _score_from_findings(analysis_result.get("findings", []))

    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    priorities = analysis_result.get("priority_findings", [])
    strongest = [item for item in priorities if item.get("status") == "pass"][:3]
    weakest = [item for item in priorities if item.get("status") in {"fail", "warning"}][:5]

    return {
        "module": "ai.scorer",
        "model": "deterministic_scoring_v1",
        "overall_score": overall,
        "grade": grade,
        "area_scores": area_scores,
        "most_important_issues": weakest,
        "strong_signals": strongest,
        "note": "Python deterministic scoring from summarized findings only.",
    }
