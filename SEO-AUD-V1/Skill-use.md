# SEO-AUD-V1 Usage Guide

## What This Skill Does
SEO-AUD-V1 audits one website URL or multiple URLs and returns structured SEO findings. The pipeline is Python-first for all detection, parsing, validation, and check logic. AI modules only summarize score, recommendations, and report writing.

Every module prints its result as JSON in the console during execution, and the final audit is saved to a JSON file per URL.

## File-by-File Purpose

### Root Files
- `main.py`: Entry point. Accepts URL input, runs the full pipeline, prints JSON stage outputs, and triggers export modules.
- `config.py`: Central settings, thresholds, retries/timeouts, API keys, and feature flags loaded from environment variables.
- `skill.json`: OpenClaw skill definition and run command examples.
- `requirements.txt`: Python dependencies required by this project.
- `Skill-use.md`: This usage and architecture guide.

### Core
- `core/crawler.py`: Fetches page HTML once using shared fetch client.
- `core/extractor.py`: Extracts structured page data once from HTML.
- `core/analyzer.py`: Runs all checks, combines findings, and produces unified summary.

### Utils
- `utils/fetch.py`: Shared HTTP layer with retries, timeout handling, redirects, and status-only checks.
- `utils/parser.py`: HTML parsing helpers to extract title, meta tags, headings, links, images, scripts, JSON-LD, and visible text.
- `utils/urls.py`: URL normalization, canonical comparison, relative URL resolution, and slug quality analysis.
- `utils/helpers.py`: JSON printing helpers, finding schema helpers, and summary utilities.

### Checks
- `checks/technical.py`: HTML structure, clean URL, sitemap, robots.txt, canonical, HTTPS, and broken links.
- `checks/onpage.py`: Title, meta description, heading hierarchy, alt text, internal links, and URL keyword checks.
- `checks/performance.py`: PageSpeed API or heuristic score, image format, lazy loading, CDN pattern, and caching headers.
- `checks/structured.py`: JSON-LD, Breadcrumb schema, Open Graph, and Twitter metadata checks.
- `checks/content.py`: FAQ presence, examples/use-cases, supporting content blocks, and hreflang language signals.
- `checks/indexing.py`: Indexability blockers, pagination signals, and thin content analysis.

### AI
- `ai/scorer.py`: Produces area-level and overall SEO score from summary findings only.
- `ai/suggestions.py`: Generates prioritized improvement actions from weak/failing checks only.
- `ai/report_writer.py`: Creates concise professional report narrative from score + suggestions.

### Output
- `output/json_report.py`: Writes one machine-readable JSON report per URL.
- `output/doc_report.py`: Writes DOCX report and optionally includes Google Docs automation handoff metadata.

## How To Install
1. Open terminal in project root (`SEO-AUD-V1`).
2. Create virtual environment:
   - Windows PowerShell: `python -m venv .venv`
3. Activate environment:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
4. Install dependencies:
   - `pip install -r requirements.txt`

## How To Run

### Audit One Website URL
```bash
python main.py --url https://example.com --keyword seo --output-dir audit_output
```

### Audit Many URLs From File
Create `urls.txt` with one URL per line:
```txt
https://example.com
https://example.com/about
https://example.com/contact
```
Run:
```bash
python main.py --urls-file urls.txt --keyword seo --output-dir audit_output
```

### Generate DOCX Report Too
```bash
python main.py --url https://example.com --doc --google-docs --output-dir audit_output
```

### Disable AI Layer (Python Checks Only)
```bash
python main.py --url https://example.com --no-ai --output-dir audit_output
```

## How Website Audit Works (End-to-End)
1. URL input is collected and normalized.
2. Crawler fetches each URL HTML and headers.
3. Extractor parses HTML once into structured fields.
4. Analyzer runs all check modules on the same structured data.
5. Findings are merged into one standard audit object.
6. AI scorer/suggestions/report writer run on summary findings only (if enabled).
7. JSON report is saved per URL.
8. DOCX report is generated if `--doc` is enabled.

## JSON Output Behavior
- Each stage prints JSON to console with:
  - `stage`
  - `timestamp_utc`
  - `result`
- Stages printed include:
  - `config`
  - `core.crawler`
  - `core.extractor`
  - `core.analyzer`
  - `ai.scorer` (when enabled)
  - `ai.suggestions` (when enabled)
  - `ai.report_writer` (when enabled)
  - `output.json_report`
  - `output.doc_report`
  - `main.summary`

## Environment Variables (Optional)
- `SEO_AUD_USER_AGENT`
- `SEO_AUD_TIMEOUT`
- `SEO_AUD_RETRIES`
- `SEO_AUD_BACKOFF`
- `SEO_AUD_MAX_LINKS`
- `SEO_AUD_TITLE_MIN`
- `SEO_AUD_TITLE_MAX`
- `SEO_AUD_META_MIN`
- `SEO_AUD_META_MAX`
- `SEO_AUD_THIN_WORDS`
- `PAGESPEED_API_KEY`
- `SERP_API_KEY`
- `SEO_AUD_ENABLE_AI`
- `SEO_AUD_ENABLE_TECHNICAL`
- `SEO_AUD_ENABLE_ONPAGE`
- `SEO_AUD_ENABLE_PERFORMANCE`
- `SEO_AUD_ENABLE_STRUCTURED`
- `SEO_AUD_ENABLE_CONTENT`
- `SEO_AUD_ENABLE_INDEXING`

## Notes
- This project is designed to keep AI usage small and stable by sending compact summary data only.
- All detection and validation logic runs in Python checks for speed and reproducibility.
- Google Docs publishing is represented as handoff metadata in phase 1 and can be connected to automation later.
