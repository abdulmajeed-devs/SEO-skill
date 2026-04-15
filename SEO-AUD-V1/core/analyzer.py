from typing import Any, Dict

from checks import content, indexing, onpage, performance, structured, technical
from utils.helpers import flatten_findings, summarize_findings, top_priority_findings


class Analyzer:
    def __init__(self, config: Any, fetch_client: Any) -> None:
        self.config = config
        self.fetch_client = fetch_client

    @staticmethod
    def _technical_signals(technical_result: Dict[str, Any]) -> Dict[str, Any]:
        robots_disallow_all = False
        for finding in technical_result.get("findings", []):
            if finding.get("check_id") == "technical_robots_disallow_all" and finding.get("status") == "fail":
                robots_disallow_all = True
                break
        return {
            "robots_disallow_all": robots_disallow_all,
        }

    def run(self, extract_result: Dict[str, Any], crawl_result: Dict[str, Any], target_keyword: str) -> Dict[str, Any]:
        parsed_page = extract_result.get("parsed", {})
        current_url = crawl_result.get("fetch", {}).get("final_url") or crawl_result.get("normalized_url", "")

        context = {
            "config": self.config,
            "fetch_client": self.fetch_client,
            "target_keyword": target_keyword,
            "max_links_to_check": getattr(self.config, "max_links_to_check", 20),
        }

        module_results: Dict[str, Dict[str, Any]] = {}

        if getattr(self.config, "enable_technical_checks", True):
            module_results["technical"] = technical.run(parsed_page, crawl_result, context)
        else:
            module_results["technical"] = {
                "module": "checks.technical",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        context["technical_signals"] = self._technical_signals(module_results["technical"])

        if getattr(self.config, "enable_onpage_checks", True):
            module_results["onpage"] = onpage.run(parsed_page, crawl_result, context)
        else:
            module_results["onpage"] = {
                "module": "checks.onpage",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        if getattr(self.config, "enable_performance_checks", True):
            module_results["performance"] = performance.run(parsed_page, crawl_result, context)
        else:
            module_results["performance"] = {
                "module": "checks.performance",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        if getattr(self.config, "enable_structured_checks", True):
            module_results["structured"] = structured.run(parsed_page, crawl_result, context)
        else:
            module_results["structured"] = {
                "module": "checks.structured",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        if getattr(self.config, "enable_content_checks", True):
            module_results["content"] = content.run(parsed_page, crawl_result, context)
        else:
            module_results["content"] = {
                "module": "checks.content",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        if getattr(self.config, "enable_indexing_checks", True):
            module_results["indexing"] = indexing.run(parsed_page, crawl_result, context)
        else:
            module_results["indexing"] = {
                "module": "checks.indexing",
                "url": current_url,
                "summary": {"total": 0, "status": {}, "severity": {}},
                "findings": [],
                "skipped": True,
            }

        all_findings = flatten_findings(module_results)
        summary = summarize_findings(all_findings)
        priorities = top_priority_findings(all_findings, limit=10)

        return {
            "module": "core.analyzer",
            "url": current_url,
            "summary": summary,
            "priority_findings": priorities,
            "modules": module_results,
            "findings": all_findings,
        }
