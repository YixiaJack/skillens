"""Minimal i18n — dict-based translations for user-facing labels.

Usage:
    from skillens.display.i18n import t, set_lang
    set_lang("zh")
    t("verdict.LEARN")  # → "值得学"
"""

from __future__ import annotations

_CURRENT = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "header.skillens": "🔍 SkiLens",
        "label.market_demand": "Market Demand",
        "label.half_life": "Skill Half-life",
        "label.info_density": "Info Density",
        "label.freshness": "Freshness",
        "label.effort": "Effort vs Return",
        "label.profile_match": "Profile Match",
        "label.overall": "Overall",
        "label.verdict": "Verdict",
        "label.strengths": "✅ Strengths",
        "label.concerns": "⚠️  Concerns",
        "label.alternatives": "💡 Alternatives",
        "label.better_alternatives": "💡 Better Alternatives Found",
        "verdict.LEARN": "LEARN",
        "verdict.SKIP": "SKIP",
        "verdict.CONSIDER_ALTERNATIVES": "CONSIDER ALTERNATIVES",
        "mode.quick": "quick mode",
        "mode.deep": "deep mode",
    },
    "zh": {
        "header.skillens": "🔍 SkiLens 学习资源评估",
        "label.market_demand": "市场需求",
        "label.half_life": "技能半衰期",
        "label.info_density": "信息密度",
        "label.freshness": "内容新鲜度",
        "label.effort": "投入产出比",
        "label.profile_match": "个人契合度",
        "label.overall": "总分",
        "label.verdict": "结论",
        "label.strengths": "✅ 优点",
        "label.concerns": "⚠️  需要注意",
        "label.alternatives": "💡 其他推荐",
        "label.better_alternatives": "💡 发现了更好的选择",
        "verdict.LEARN": "值得学",
        "verdict.SKIP": "跳过",
        "verdict.CONSIDER_ALTERNATIVES": "看看其他选项",
        "mode.quick": "快速模式",
        "mode.deep": "深度模式",
    },
}


def set_lang(lang: str) -> None:
    global _CURRENT
    _CURRENT = lang if lang in _STRINGS else "en"


def get_lang() -> str:
    return _CURRENT


def t(key: str) -> str:
    """Translate a key for the current language, falling back to English."""
    return _STRINGS.get(_CURRENT, {}).get(key) or _STRINGS["en"].get(key) or key


def resolve_lang(requested: str, url: str | None = None) -> str:
    """Auto-detect language.

    - If requested is explicit ("en" / "zh"), use it.
    - If "auto", try the config; then check URL for .cn / .zh hints.
    """
    if requested in _STRINGS:
        return requested
    if requested == "auto":
        try:
            from skillens.core.config import get_value

            cfg = get_value("lang")
            if cfg and cfg in _STRINGS:
                return cfg
        except Exception:
            pass
        if url and (".cn/" in url or "zhihu.com" in url or "bilibili.com" in url):
            return "zh"
    return "en"
