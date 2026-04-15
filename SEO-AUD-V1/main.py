import argparse
from typing import Any, Dict, List

from ai.report_writer import run as write_ai_report
from ai.scorer import run as run_ai_scorer
from ai.suggestions import run as run_ai_suggestions
from config import load_config
from core.analyzer import Analyzer
from core.crawler import Crawler
from core.extractor import Extractor
from output.doc_report import run as write_doc_report
from output.json_report import run as write_json_report
from utils.helpers import print_json_stage, utc_now_iso


def _read_urls_file(file_path: str) -> List[str]:
    urls: List[str] = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def _collect_urls(url_args: List[str] | None, urls_file: str | None) -> List[str]:
    collected: List[str] = []
    if url_args:
        collected.extend(url_args)
    if urls_file:
        collected.extend(_read_urls_file(urls_file))

    deduped: List[str] = []
    seen = set()
    for item in collected:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _compact_crawl_for_output(crawl_result: Dict[str, Any]) -> Dict[str, Any]:
    cloned = dict(crawl_result)
    fetch_data = dict(cloned.get("fetch", {}))
    html = fetch_data.get("html", "")
    if isinstance(html, str) and html:
        fetch_data["html"] = f"<omitted raw html, length={len(html)}>"
    cloned["fetch"] = fetch_data
    return cloned


def run_audit(
    urls: List[str],
    target_keyword: str,
    output_dir: str,
    generate_doc: bool,
    disable_ai: bool,
    enable_google_docs: bool,
) -> Dict[str, Any]:
    config = load_config()
    print_json_stage("config", {"module": "config.py", "config": config.to_public_dict()})

    crawler = Crawler(config)
    extractor = Extractor()
    analyzer = Analyzer(config=config, fetch_client=crawler.fetch_client)

    all_audits: List[Dict[str, Any]] = []

    try:
        for source_url in urls:
            crawl_result = crawler.fetch(source_url)
            print_json_stage("core.crawler", crawl_result)

            extract_result = extractor.extract(crawl_result)
            print_json_stage("core.extractor", extract_result)

            analysis_result = analyzer.run(
                extract_result=extract_result,
                crawl_result=crawl_result,
                target_keyword=target_keyword,
            )
            print_json_stage("core.analyzer", analysis_result)

            ai_payload: Dict[str, Any] = {
                "enabled": False,
                "reason": "AI disabled by config or CLI",
            }

            if config.enable_ai and not disable_ai:
                score_result = run_ai_scorer(analysis_result=analysis_result, config=config)
                print_json_stage("ai.scorer", score_result)

                suggestions_result = run_ai_suggestions(
                    analysis_result=analysis_result,
                    score_result=score_result,
                    config=config,
                )
                print_json_stage("ai.suggestions", suggestions_result)

                report_result = write_ai_report(
                    analysis_result=analysis_result,
                    score_result=score_result,
                    suggestions_result=suggestions_result,
                    config=config,
                )
                print_json_stage("ai.report_writer", report_result)

                ai_payload = {
                    "enabled": True,
                    "score": score_result,
                    "suggestions": suggestions_result,
                    "report": report_result,
                }

            final_audit = {
                "url": analysis_result.get("url") or source_url,
                "timestamp_utc": utc_now_iso(),
                "crawl": _compact_crawl_for_output(crawl_result),
                "extract": extract_result,
                "analysis": analysis_result,
                "ai": ai_payload,
            }

            json_output = write_json_report(
                final_audit=final_audit,
                output_dir=output_dir,
            )
            print_json_stage("output.json_report", json_output)

            doc_output = {
                "module": "output.doc_report",
                "status": "skipped",
                "reason": "Use --doc to generate document output",
            }
            if generate_doc:
                doc_output = write_doc_report(
                    final_audit=final_audit,
                    output_dir=output_dir,
                    enable_google_docs=enable_google_docs,
                )
            print_json_stage("output.doc_report", doc_output)

            all_audits.append(
                {
                    "url": final_audit["url"],
                    "json_output": json_output,
                    "doc_output": doc_output,
                    "analysis_summary": analysis_result.get("summary", {}),
                }
            )
    finally:
        crawler.close()

    summary = {
        "module": "main.py",
        "audits_run": len(all_audits),
        "urls": [item.get("url") for item in all_audits],
        "outputs": all_audits,
    }
    print_json_stage("main.summary", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="SEO-AUD-V1 website auditor")
    parser.add_argument("--url", action="append", help="Single URL. Repeat for many URLs.")
    parser.add_argument("--urls-file", help="Path to text file with one URL per line.")
    parser.add_argument("--keyword", default="", help="Target keyword for URL relevance checks.")
    parser.add_argument("--output-dir", default="audit_output", help="Folder for report files.")
    parser.add_argument("--doc", action="store_true", help="Generate document report output.")
    parser.add_argument(
        "--google-docs",
        action="store_true",
        help="Add Google Docs handoff metadata in doc report output.",
    )
    parser.add_argument("--no-ai", action="store_true", help="Disable AI modules.")
    args = parser.parse_args()

    urls = _collect_urls(args.url, args.urls_file)
    if not urls:
        parser.error("Provide at least one URL via --url or --urls-file")

    run_audit(
        urls=urls,
        target_keyword=args.keyword,
        output_dir=args.output_dir,
        generate_doc=args.doc,
        disable_ai=args.no_ai,
        enable_google_docs=args.google_docs,
    )


if __name__ == "__main__":
    main()
