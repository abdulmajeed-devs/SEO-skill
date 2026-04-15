import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return cleaned.strip("_") or "audit"


def compact_text(value: str, max_len: int = 400) -> str:
    if not isinstance(value, str):
        return value
    if len(value) <= max_len:
        return value
    remainder = len(value) - max_len
    return f"{value[:max_len]}...<trimmed {remainder} chars>"


def to_json_safe(value: Any, max_text_len: int = 400) -> Any:
    if isinstance(value, dict):
        return {str(k): to_json_safe(v, max_text_len=max_text_len) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item, max_text_len=max_text_len) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item, max_text_len=max_text_len) for item in value]
    if isinstance(value, str):
        return compact_text(value, max_len=max_text_len)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def print_json_stage(stage: str, result: Dict[str, Any]) -> None:
    payload = {
        "stage": stage,
        "timestamp_utc": utc_now_iso(),
        "result": to_json_safe(result),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def make_finding(
    check_id: str,
    status: str,
    severity: str,
    message: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {},
    }


def summarize_findings(findings: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    total = 0
    counts = {
        "pass": 0,
        "fail": 0,
        "warning": 0,
        "info": 0,
    }
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for finding in findings:
        total += 1
        status = finding.get("status", "info")
        severity = finding.get("severity", "low")
        if status in counts:
            counts[status] += 1
        else:
            counts["info"] += 1
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts["low"] += 1

    return {
        "total": total,
        "status": counts,
        "severity": severity_counts,
    }


def flatten_findings(modules: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_findings: List[Dict[str, Any]] = []
    for module_name, module_result in modules.items():
        for finding in module_result.get("findings", []):
            enriched = deepcopy(finding)
            enriched["module"] = module_name
            all_findings.append(enriched)
    return all_findings


def top_priority_findings(findings: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    severity_rank = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }
    status_rank = {
        "fail": 0,
        "warning": 1,
        "pass": 2,
        "info": 3,
    }
    sorted_findings = sorted(
        findings,
        key=lambda item: (
            severity_rank.get(item.get("severity", "low"), 3),
            status_rank.get(item.get("status", "info"), 3),
        ),
    )
    return sorted_findings[:limit]
