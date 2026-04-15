from typing import Any, Dict, List
from urllib.parse import urlparse

from utils.helpers import make_finding, summarize_findings


OLD_IMAGE_FORMATS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff"}
MODERN_IMAGE_FORMATS = {"webp", "avif", "svg"}


def _ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if "." not in path:
        return ""
    return path.rsplit(".", 1)[-1]


def _check_pagespeed(crawl_result: Dict[str, Any], current_url: str, context: Dict[str, Any]) -> Dict[str, Any]:
    config = context.get("config")
    api_key = getattr(config, "pagespeed_api_key", "") if config else ""
    fetch_client = context.get("fetch_client")

    if api_key and fetch_client is not None:
        endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        strategy_scores: Dict[str, int] = {}
        try:
            for strategy in ["mobile", "desktop"]:
                response = fetch_client.session.get(
                    endpoint,
                    params={
                        "url": current_url,
                        "strategy": strategy,
                        "key": api_key,
                    },
                    timeout=fetch_client.timeout,
                )
                payload = response.json() if response.ok else {}
                score = (
                    payload.get("lighthouseResult", {})
                    .get("categories", {})
                    .get("performance", {})
                    .get("score")
                )
                if isinstance(score, (int, float)):
                    strategy_scores[strategy] = int(score * 100)

            if strategy_scores:
                avg_score = int(sum(strategy_scores.values()) / len(strategy_scores))
                status = "pass" if avg_score >= 75 else "warning" if avg_score >= 50 else "fail"
                severity = "low" if avg_score >= 75 else "medium" if avg_score >= 50 else "high"
                return make_finding(
                    check_id="performance_pagespeed",
                    status=status,
                    severity=severity,
                    message="PageSpeed API scores collected.",
                    details={"scores": strategy_scores, "average": avg_score, "source": "pagespeed_api"},
                )
        except Exception as exc:
            return make_finding(
                check_id="performance_pagespeed",
                status="warning",
                severity="medium",
                message="PageSpeed API call failed. Falling back to request latency heuristic.",
                details={"error": str(exc)},
            )

    elapsed_ms = crawl_result.get("fetch", {}).get("elapsed_ms", 0)
    if elapsed_ms <= 0:
        estimated_score = 50
    elif elapsed_ms <= 800:
        estimated_score = 88
    elif elapsed_ms <= 1500:
        estimated_score = 72
    elif elapsed_ms <= 2500:
        estimated_score = 58
    else:
        estimated_score = 40

    status = "pass" if estimated_score >= 75 else "warning" if estimated_score >= 50 else "fail"
    severity = "low" if estimated_score >= 75 else "medium" if estimated_score >= 50 else "high"
    return make_finding(
        check_id="performance_pagespeed",
        status=status,
        severity=severity,
        message="PageSpeed estimate generated from fetch latency.",
        details={"estimated_score": estimated_score, "elapsed_ms": elapsed_ms, "source": "heuristic"},
    )


def _check_image_format(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    images = parsed_page.get("images", [])
    if not images:
        return make_finding(
            check_id="performance_image_format",
            status="info",
            severity="low",
            message="No images found.",
            details={"images": 0},
        )

    old_count = 0
    modern_count = 0
    unknown_count = 0

    for image in images:
        ext = _ext_from_url(image.get("src", ""))
        if ext in OLD_IMAGE_FORMATS:
            old_count += 1
        elif ext in MODERN_IMAGE_FORMATS:
            modern_count += 1
        else:
            unknown_count += 1

    if modern_count >= old_count:
        return make_finding(
            check_id="performance_image_format",
            status="pass",
            severity="low",
            message="Image format usage is reasonably modern.",
            details={
                "old_formats": old_count,
                "modern_formats": modern_count,
                "unknown_formats": unknown_count,
            },
        )

    return make_finding(
        check_id="performance_image_format",
        status="warning",
        severity="medium",
        message="Modern image format adoption can be improved.",
        details={
            "old_formats": old_count,
            "modern_formats": modern_count,
            "unknown_formats": unknown_count,
        },
    )


def _check_lazy_load(parsed_page: Dict[str, Any]) -> Dict[str, Any]:
    images = parsed_page.get("images", [])
    if not images:
        return make_finding(
            check_id="performance_lazy_load",
            status="info",
            severity="low",
            message="No images found for lazy loading check.",
            details={"images": 0},
        )

    lazy_count = len([img for img in images if img.get("loading") == "lazy"])
    ratio = lazy_count / len(images)

    if len(images) <= 2 or ratio >= 0.5:
        return make_finding(
            check_id="performance_lazy_load",
            status="pass",
            severity="low",
            message="Lazy loading usage looks good.",
            details={"images": len(images), "lazy": lazy_count, "coverage": round(ratio, 2)},
        )

    return make_finding(
        check_id="performance_lazy_load",
        status="warning",
        severity="medium",
        message="More non-critical images should be lazy-loaded.",
        details={"images": len(images), "lazy": lazy_count, "coverage": round(ratio, 2)},
    )


def _check_cdn(parsed_page: Dict[str, Any], current_url: str) -> Dict[str, Any]:
    page_domain = urlparse(current_url).netloc.lower()
    asset_hosts = set()

    for image in parsed_page.get("images", []):
        src = image.get("src", "")
        host = urlparse(src).netloc.lower()
        if host:
            asset_hosts.add(host)

    for script in parsed_page.get("scripts", []):
        src = script.get("src", "")
        host = urlparse(src).netloc.lower()
        if host:
            asset_hosts.add(host)

    if not asset_hosts:
        return make_finding(
            check_id="performance_cdn",
            status="info",
            severity="low",
            message="No external assets found to assess CDN usage.",
            details={"asset_hosts": []},
        )

    external_hosts = [host for host in asset_hosts if host != page_domain]
    cdn_like = [host for host in external_hosts if any(token in host for token in ["cdn", "cloudfront", "akamai", "fastly", "jsdelivr"])]

    if cdn_like:
        return make_finding(
            check_id="performance_cdn",
            status="pass",
            severity="low",
            message="CDN-style asset delivery detected.",
            details={"cdn_hosts": cdn_like, "external_hosts": external_hosts},
        )

    if external_hosts:
        return make_finding(
            check_id="performance_cdn",
            status="warning",
            severity="low",
            message="External asset hosts found, but no clear CDN hostname pattern.",
            details={"external_hosts": external_hosts},
        )

    return make_finding(
        check_id="performance_cdn",
        status="warning",
        severity="medium",
        message="Assets appear to be served only from origin domain.",
        details={"asset_hosts": list(asset_hosts), "origin_domain": page_domain},
    )


def _check_caching(crawl_result: Dict[str, Any]) -> Dict[str, Any]:
    headers = crawl_result.get("fetch", {}).get("headers", {})
    cache_control = (headers.get("cache-control") or "").lower()
    etag = headers.get("etag", "")
    expires = headers.get("expires", "")

    if not cache_control and not etag and not expires:
        return make_finding(
            check_id="performance_caching",
            status="warning",
            severity="medium",
            message="Caching headers are missing.",
            details={"cache_control": cache_control, "etag": etag, "expires": expires},
        )

    if "no-store" in cache_control:
        return make_finding(
            check_id="performance_caching",
            status="warning",
            severity="high",
            message="Cache-Control contains no-store, limiting browser caching.",
            details={"cache_control": cache_control, "etag": etag, "expires": expires},
        )

    return make_finding(
        check_id="performance_caching",
        status="pass",
        severity="low",
        message="Caching headers are present.",
        details={"cache_control": cache_control, "etag": etag, "expires": expires},
    )


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    findings: List[Dict[str, Any]] = [
        _check_pagespeed(crawl_result=crawl_result, current_url=current_url, context=context),
        _check_image_format(parsed_page),
        _check_lazy_load(parsed_page),
        _check_cdn(parsed_page, current_url),
        _check_caching(crawl_result),
    ]

    return {
        "module": "checks.performance",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
