import re
from typing import Any, Dict
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse


def remove_fragment(url: str) -> str:
    parsed = urlparse(url.strip())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def normalize_url(url: str, default_scheme: str = "https") -> str:
    if not url or not isinstance(url, str):
        return ""

    candidate = url.strip()
    if not candidate:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        candidate = f"{default_scheme}://{candidate}"

    parsed = urlparse(candidate)
    if not parsed.netloc:
        return ""

    scheme = (parsed.scheme or default_scheme).lower()
    netloc = parsed.netloc.lower()

    path = parsed.path or "/"
    path = quote(unquote(path), safe="/%:@+-._~")
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query = urlencode(query_items, doseq=True)

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return remove_fragment(normalized)


def resolve_relative(base_url: str, candidate_url: str) -> str:
    if not candidate_url:
        return ""
    return normalize_url(urljoin(base_url, candidate_url))


def domain_of(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    return parsed.netloc.lower()


def is_same_domain(url_a: str, url_b: str) -> bool:
    return domain_of(url_a) == domain_of(url_b)


def canonical_equal(url_a: str, url_b: str) -> bool:
    norm_a = normalize_url(url_a)
    norm_b = normalize_url(url_b)
    return norm_a == norm_b


def slug_quality(url: str) -> Dict[str, Any]:
    normalized = normalize_url(url)
    if not normalized:
        return {
            "is_clean": False,
            "issues": ["invalid_url"],
            "slug": "",
            "has_query": False,
        }

    parsed = urlparse(normalized)
    slug = parsed.path.strip("/")
    issues = []

    if len(normalized) > 120:
        issues.append("url_too_long")
    if parsed.query:
        issues.append("contains_query_parameters")
    if re.search(r"[^a-zA-Z0-9\-/_]", parsed.path):
        issues.append("unsafe_characters")
    if re.search(r"\d{6,}", slug):
        issues.append("slug_looks_random")
    if slug and re.search(r"_{2,}|-{3,}", slug):
        issues.append("slug_not_readable")

    return {
        "is_clean": len(issues) == 0,
        "issues": issues,
        "slug": slug,
        "has_query": bool(parsed.query),
    }
