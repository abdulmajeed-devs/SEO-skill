import json
import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from utils.urls import domain_of, resolve_relative


def _normalize_whitespace(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _extract_meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for node in soup.find_all("meta"):
        key = node.get("name") or node.get("property") or node.get("http-equiv")
        value = node.get("content", "")
        if key:
            data[key.strip().lower()] = _normalize_whitespace(value)
    return data


def _extract_headings(soup: BeautifulSoup) -> Dict[str, List[str]]:
    output: Dict[str, List[str]] = {}
    for level in range(1, 7):
        tag = f"h{level}"
        output[tag] = [_normalize_whitespace(node.get_text(" ")) for node in soup.find_all(tag)]
        output[tag] = [item for item in output[tag] if item]
    return output


def _extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    base_domain = domain_of(base_url)
    links: List[Dict[str, Any]] = []
    for node in soup.find_all("a", href=True):
        href = resolve_relative(base_url, node.get("href", "").strip())
        if not href:
            continue
        links.append(
            {
                "url": href,
                "text": _normalize_whitespace(node.get_text(" ")),
                "rel": " ".join(node.get("rel", [])),
                "is_internal": domain_of(href) == base_domain,
            }
        )
    return links


def _extract_images(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    for node in soup.find_all("img"):
        src = resolve_relative(base_url, node.get("src", "").strip()) if node.get("src") else ""
        if not src:
            continue
        images.append(
            {
                "src": src,
                "alt": _normalize_whitespace(node.get("alt", "")),
                "title": _normalize_whitespace(node.get("title", "")),
                "loading": (node.get("loading", "") or "").strip().lower(),
            }
        )
    return images


def _extract_scripts(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    scripts: List[Dict[str, Any]] = []
    for node in soup.find_all("script"):
        src = node.get("src", "").strip()
        resolved = resolve_relative(base_url, src) if src else ""
        scripts.append(
            {
                "src": resolved,
                "async": bool(node.get("async")),
                "defer": bool(node.get("defer")),
                "inline": not bool(resolved),
            }
        )
    return scripts


def _extract_jsonld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    nodes = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    for node in nodes:
        raw = (node.string or node.get_text() or "").strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            parsed_items = parsed if isinstance(parsed, list) else [parsed]
            for item in parsed_items:
                if isinstance(item, dict):
                    schema_type = item.get("@type")
                    if isinstance(schema_type, list):
                        schema_types = [str(x) for x in schema_type]
                    elif schema_type:
                        schema_types = [str(schema_type)]
                    else:
                        schema_types = []
                    blocks.append(
                        {
                            "valid": True,
                            "types": schema_types,
                            "data": item,
                            "error": "",
                        }
                    )
                else:
                    blocks.append(
                        {
                            "valid": False,
                            "types": [],
                            "data": {},
                            "error": "jsonld_item_not_object",
                        }
                    )
        except json.JSONDecodeError as exc:
            blocks.append(
                {
                    "valid": False,
                    "types": [],
                    "data": {},
                    "error": f"json_decode_error: {exc}",
                }
            )
    return blocks


def _extract_visible_text(soup: BeautifulSoup) -> str:
    clone = BeautifulSoup(str(soup), "lxml")
    for node in clone(["script", "style", "noscript", "template"]):
        node.decompose()
    return _normalize_whitespace(clone.get_text(" "))


def parse_html_document(html: str, base_url: str) -> Dict[str, Any]:
    if not html:
        return {
            "parse_error": "empty_html",
            "title": "",
            "meta_tags": {},
            "headings": {f"h{i}": [] for i in range(1, 7)},
            "links": [],
            "images": [],
            "scripts": [],
            "jsonld": [],
            "visible_text": "",
            "word_count": 0,
            "canonical": "",
            "hreflang": [],
            "rel_links": {},
            "tag_presence": {},
        }

    soup = BeautifulSoup(html, "lxml")

    title_node = soup.find("title")
    title = _normalize_whitespace(title_node.get_text(" ")) if title_node else ""

    meta_tags = _extract_meta_tags(soup)
    headings = _extract_headings(soup)
    links = _extract_links(soup, base_url)
    images = _extract_images(soup, base_url)
    scripts = _extract_scripts(soup, base_url)
    jsonld = _extract_jsonld(soup)

    visible_text = _extract_visible_text(soup)
    word_count = len([token for token in visible_text.split(" ") if token])

    canonical = ""
    canonical_node = soup.find("link", rel=lambda value: value and "canonical" in [x.lower() for x in value])
    if canonical_node and canonical_node.get("href"):
        canonical = resolve_relative(base_url, canonical_node.get("href", ""))

    hreflang: List[Dict[str, str]] = []
    for node in soup.find_all("link", rel=lambda value: value and "alternate" in [x.lower() for x in value]):
        lang = (node.get("hreflang") or "").strip()
        href = resolve_relative(base_url, node.get("href", "")) if node.get("href") else ""
        if lang and href:
            hreflang.append({"lang": lang, "href": href})

    rel_links: Dict[str, str] = {}
    for node in soup.find_all("link", rel=True):
        rel_values = [x.lower() for x in node.get("rel", [])]
        href = resolve_relative(base_url, node.get("href", "")) if node.get("href") else ""
        if "next" in rel_values and href:
            rel_links["next"] = href
        if "prev" in rel_values and href:
            rel_links["prev"] = href

    tag_presence = {
        "html": len(soup.find_all("html")),
        "head": len(soup.find_all("head")),
        "body": len(soup.find_all("body")),
        "header": len(soup.find_all("header")),
        "nav": len(soup.find_all("nav")),
        "main": len(soup.find_all("main")),
        "article": len(soup.find_all("article")),
        "footer": len(soup.find_all("footer")),
    }

    return {
        "parse_error": "",
        "title": title,
        "meta_tags": meta_tags,
        "headings": headings,
        "links": links,
        "images": images,
        "scripts": scripts,
        "jsonld": jsonld,
        "visible_text": visible_text,
        "word_count": word_count,
        "canonical": canonical,
        "hreflang": hreflang,
        "rel_links": rel_links,
        "tag_presence": tag_presence,
    }
