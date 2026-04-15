from typing import Any, Dict, List
from urllib.parse import urlparse

from utils.helpers import make_finding, summarize_findings
from utils.urls import canonical_equal, normalize_url, slug_quality


def _site_root(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _check_html_structure(parsed_page: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    tags = parsed_page.get("tag_presence", {})

    missing = [tag for tag in ["html", "head", "body"] if tags.get(tag, 0) == 0]
    if missing:
        findings.append(
            make_finding(
                check_id="technical_html_structure",
                status="fail",
                severity="high",
                message="Missing required document structure tags.",
                details={"missing_tags": missing},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_html_structure",
                status="pass",
                severity="low",
                message="Core document structure tags are present.",
                details={"tags": tags},
            )
        )

    landmark_total = tags.get("header", 0) + tags.get("nav", 0) + tags.get("main", 0) + tags.get("footer", 0)
    if landmark_total < 3:
        findings.append(
            make_finding(
                check_id="technical_landmarks",
                status="warning",
                severity="medium",
                message="Landmark tags are limited. Add semantic layout tags for better structure.",
                details={"tag_presence": tags},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_landmarks",
                status="pass",
                severity="low",
                message="Landmark tags are present.",
                details={"tag_presence": tags},
            )
        )

    h1_count = len(parsed_page.get("headings", {}).get("h1", []))
    if h1_count != 1:
        findings.append(
            make_finding(
                check_id="technical_heading_hierarchy_support",
                status="warning",
                severity="medium",
                message="Heading hierarchy support is weak because H1 count is not exactly 1.",
                details={"h1_count": h1_count},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_heading_hierarchy_support",
                status="pass",
                severity="low",
                message="H1 hierarchy baseline is valid.",
                details={"h1_count": h1_count},
            )
        )

    return findings


def _check_clean_url(current_url: str) -> List[Dict[str, Any]]:
    quality = slug_quality(current_url)
    if quality.get("is_clean"):
        return [
            make_finding(
                check_id="technical_clean_url",
                status="pass",
                severity="low",
                message="URL appears clean and readable.",
                details=quality,
            )
        ]

    return [
        make_finding(
            check_id="technical_clean_url",
            status="warning",
            severity="medium",
            message="URL may not be SEO-friendly.",
            details=quality,
        )
    ]


def _check_sitemap(current_url: str, fetch_client: Any) -> List[Dict[str, Any]]:
    root = _site_root(current_url)
    if not root:
        return [
            make_finding(
                check_id="technical_sitemap",
                status="fail",
                severity="high",
                message="Cannot determine site root for sitemap checks.",
                details={"url": current_url},
            )
        ]

    sitemap_paths = ["/sitemap.xml", "/sitemap_index.xml"]
    for path in sitemap_paths:
        sitemap_url = f"{root}{path}"
        result = fetch_client.fetch(sitemap_url, method="GET")
        html = (result.get("html") or "").lower()
        if result.get("status_code") == 200 and ("<urlset" in html or "<sitemapindex" in html):
            return [
                make_finding(
                    check_id="technical_sitemap",
                    status="pass",
                    severity="low",
                    message="Sitemap found and appears valid.",
                    details={"sitemap_url": sitemap_url},
                )
            ]

    return [
        make_finding(
            check_id="technical_sitemap",
            status="fail",
            severity="high",
            message="Sitemap not found or not valid XML sitemap format.",
            details={"tested_paths": sitemap_paths, "site_root": root},
        )
    ]


def _check_robots(current_url: str, fetch_client: Any) -> List[Dict[str, Any]]:
    root = _site_root(current_url)
    robots_url = f"{root}/robots.txt" if root else ""
    if not robots_url:
        return [
            make_finding(
                check_id="technical_robots",
                status="fail",
                severity="high",
                message="Cannot determine robots.txt location.",
                details={"url": current_url},
            )
        ]

    result = fetch_client.fetch(robots_url, method="GET")
    status_code = result.get("status_code", 0)
    body = result.get("html", "")

    if status_code != 200 or not body:
        return [
            make_finding(
                check_id="technical_robots",
                status="fail",
                severity="high",
                message="robots.txt missing or inaccessible.",
                details={"robots_url": robots_url, "status_code": status_code},
            )
        ]

    body_lower = body.lower()
    has_sitemap = "sitemap:" in body_lower
    disallow_all = "user-agent: *" in body_lower and "disallow: /" in body_lower

    findings = [
        make_finding(
            check_id="technical_robots",
            status="pass",
            severity="low",
            message="robots.txt fetched successfully.",
            details={"robots_url": robots_url, "status_code": status_code},
        )
    ]

    if has_sitemap:
        findings.append(
            make_finding(
                check_id="technical_robots_sitemap_reference",
                status="pass",
                severity="low",
                message="robots.txt includes a sitemap reference.",
                details={"robots_url": robots_url},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_robots_sitemap_reference",
                status="warning",
                severity="medium",
                message="No sitemap reference found in robots.txt.",
                details={"robots_url": robots_url},
            )
        )

    if disallow_all:
        findings.append(
            make_finding(
                check_id="technical_robots_disallow_all",
                status="fail",
                severity="critical",
                message="robots.txt appears to block all crawling for default user-agent.",
                details={"robots_url": robots_url},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_robots_disallow_all",
                status="pass",
                severity="low",
                message="No global crawl block detected in robots.txt.",
                details={"robots_url": robots_url},
            )
        )

    return findings


def _check_canonical(parsed_page: Dict[str, Any], current_url: str) -> List[Dict[str, Any]]:
    canonical = parsed_page.get("canonical", "")
    if not canonical:
        return [
            make_finding(
                check_id="technical_canonical",
                status="warning",
                severity="medium",
                message="Canonical tag is missing.",
                details={"current_url": current_url},
            )
        ]

    if canonical_equal(canonical, current_url):
        return [
            make_finding(
                check_id="technical_canonical",
                status="pass",
                severity="low",
                message="Canonical matches current URL.",
                details={"canonical": canonical, "current_url": current_url},
            )
        ]

    return [
        make_finding(
            check_id="technical_canonical",
            status="warning",
            severity="medium",
            message="Canonical URL differs from current URL.",
            details={"canonical": canonical, "current_url": current_url},
        )
    ]


def _check_https(crawl_result: Dict[str, Any], fetch_client: Any) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    final_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

    if final_url.startswith("https://"):
        findings.append(
            make_finding(
                check_id="technical_https",
                status="pass",
                severity="low",
                message="Page is served over HTTPS.",
                details={"final_url": final_url},
            )
        )
    else:
        findings.append(
            make_finding(
                check_id="technical_https",
                status="fail",
                severity="critical",
                message="Page is not served over HTTPS.",
                details={"final_url": final_url},
            )
        )

    parsed = urlparse(final_url)
    if parsed.netloc:
        http_url = f"http://{parsed.netloc}{parsed.path or '/'}"
        if parsed.query:
            http_url = f"{http_url}?{parsed.query}"
        redirect_result = fetch_client.fetch_status(http_url)
        redirect_target = redirect_result.get("final_url", "")
        if redirect_target.startswith("https://"):
            findings.append(
                make_finding(
                    check_id="technical_http_to_https_redirect",
                    status="pass",
                    severity="low",
                    message="HTTP requests redirect to HTTPS.",
                    details={"http_url": http_url, "redirect_target": redirect_target},
                )
            )
        else:
            findings.append(
                make_finding(
                    check_id="technical_http_to_https_redirect",
                    status="warning",
                    severity="high",
                    message="HTTP to HTTPS redirect is not clearly enforced.",
                    details={"http_url": http_url, "redirect_target": redirect_target},
                )
            )

    return findings


def _check_broken_links(parsed_page: Dict[str, Any], fetch_client: Any, max_links_to_check: int) -> List[Dict[str, Any]]:
    links = parsed_page.get("links", [])
    checked = 0
    broken: List[Dict[str, Any]] = []

    for link in links:
        if checked >= max_links_to_check:
            break
        link_url = link.get("url", "")
        if not link_url.startswith("http"):
            continue

        status_result = fetch_client.fetch_status(link_url)
        status_code = status_result.get("status_code", 0)
        error = status_result.get("error", "")
        checked += 1

        if status_code >= 400 or status_code == 0 or error:
            broken.append(
                {
                    "url": link_url,
                    "status_code": status_code,
                    "error": error,
                    "is_internal": bool(link.get("is_internal")),
                }
            )

    if not links:
        return [
            make_finding(
                check_id="technical_broken_links",
                status="info",
                severity="low",
                message="No links found to validate.",
                details={"checked": 0, "broken": 0},
            )
        ]

    if not broken:
        return [
            make_finding(
                check_id="technical_broken_links",
                status="pass",
                severity="low",
                message="No broken links detected in sampled links.",
                details={"checked": checked, "broken": 0},
            )
        ]

    internal_broken = len([item for item in broken if item.get("is_internal")])
    severity = "high" if internal_broken > 0 else "medium"
    return [
        make_finding(
            check_id="technical_broken_links",
            status="fail",
            severity=severity,
            message="Broken links were detected.",
            details={
                "checked": checked,
                "broken_total": len(broken),
                "broken_internal": internal_broken,
                "broken_external": len(broken) - internal_broken,
                "examples": broken[:10],
            },
        )
    ]


def run(parsed_page: Dict[str, Any], crawl_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")
    fetch_client = context.get("fetch_client")
    max_links_to_check = int(context.get("max_links_to_check", 20))

    findings.extend(_check_html_structure(parsed_page))
    findings.extend(_check_clean_url(current_url))
    findings.extend(_check_canonical(parsed_page, current_url))

    if fetch_client is None:
        findings.append(
            make_finding(
                check_id="technical_network_checks",
                status="warning",
                severity="high",
                message="Network-level technical checks skipped because fetch client is unavailable.",
                details={},
            )
        )
    else:
        findings.extend(_check_sitemap(current_url, fetch_client))
        findings.extend(_check_robots(current_url, fetch_client))
        findings.extend(_check_https(crawl_result, fetch_client))
        findings.extend(_check_broken_links(parsed_page, fetch_client, max_links_to_check))

    return {
        "module": "checks.technical",
        "url": current_url,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
