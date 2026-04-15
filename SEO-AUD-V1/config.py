import os
from dataclasses import dataclass, field
from typing import Any, Dict


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    user_agent: str = "SEO-AUD-V1/1.0 (+https://openclaw.local)"
    request_timeout: int = 15
    request_retries: int = 2
    retry_backoff_seconds: float = 1.0
    max_links_to_check: int = 20

    title_min_length: int = 30
    title_max_length: int = 65
    meta_desc_min_length: int = 120
    meta_desc_max_length: int = 160
    thin_content_word_threshold: int = 300

    pagespeed_api_key: str = ""
    serp_api_key: str = ""

    enable_ai: bool = True
    enable_technical_checks: bool = True
    enable_onpage_checks: bool = True
    enable_performance_checks: bool = True
    enable_structured_checks: bool = True
    enable_content_checks: bool = True
    enable_indexing_checks: bool = True

    feature_flags: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        cfg = cls(
            user_agent=os.getenv("SEO_AUD_USER_AGENT", cls.user_agent),
            request_timeout=_env_int("SEO_AUD_TIMEOUT", cls.request_timeout),
            request_retries=_env_int("SEO_AUD_RETRIES", cls.request_retries),
            retry_backoff_seconds=_env_float("SEO_AUD_BACKOFF", cls.retry_backoff_seconds),
            max_links_to_check=_env_int("SEO_AUD_MAX_LINKS", cls.max_links_to_check),
            title_min_length=_env_int("SEO_AUD_TITLE_MIN", cls.title_min_length),
            title_max_length=_env_int("SEO_AUD_TITLE_MAX", cls.title_max_length),
            meta_desc_min_length=_env_int("SEO_AUD_META_MIN", cls.meta_desc_min_length),
            meta_desc_max_length=_env_int("SEO_AUD_META_MAX", cls.meta_desc_max_length),
            thin_content_word_threshold=_env_int(
                "SEO_AUD_THIN_WORDS",
                cls.thin_content_word_threshold,
            ),
            pagespeed_api_key=os.getenv("PAGESPEED_API_KEY", ""),
            serp_api_key=os.getenv("SERP_API_KEY", ""),
            enable_ai=_env_bool("SEO_AUD_ENABLE_AI", True),
            enable_technical_checks=_env_bool("SEO_AUD_ENABLE_TECHNICAL", True),
            enable_onpage_checks=_env_bool("SEO_AUD_ENABLE_ONPAGE", True),
            enable_performance_checks=_env_bool("SEO_AUD_ENABLE_PERFORMANCE", True),
            enable_structured_checks=_env_bool("SEO_AUD_ENABLE_STRUCTURED", True),
            enable_content_checks=_env_bool("SEO_AUD_ENABLE_CONTENT", True),
            enable_indexing_checks=_env_bool("SEO_AUD_ENABLE_INDEXING", True),
        )
        cfg.feature_flags = {
            "ai": cfg.enable_ai,
            "technical": cfg.enable_technical_checks,
            "onpage": cfg.enable_onpage_checks,
            "performance": cfg.enable_performance_checks,
            "structured": cfg.enable_structured_checks,
            "content": cfg.enable_content_checks,
            "indexing": cfg.enable_indexing_checks,
        }
        return cfg

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "user_agent": self.user_agent,
            "request_timeout": self.request_timeout,
            "request_retries": self.request_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "max_links_to_check": self.max_links_to_check,
            "title_min_length": self.title_min_length,
            "title_max_length": self.title_max_length,
            "meta_desc_min_length": self.meta_desc_min_length,
            "meta_desc_max_length": self.meta_desc_max_length,
            "thin_content_word_threshold": self.thin_content_word_threshold,
            "pagespeed_api_key": "set" if bool(self.pagespeed_api_key) else "not_set",
            "serp_api_key": "set" if bool(self.serp_api_key) else "not_set",
            "feature_flags": self.feature_flags,
        }


def load_config() -> Config:
    return Config.from_env()
