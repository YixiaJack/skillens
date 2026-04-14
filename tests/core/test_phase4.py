"""Tests for Phase 4: plugin system, dataset, i18n, MCP builder."""

import pytest

from skillens.core.dataset import _load, demand_for, halflife_for
from skillens.core.models import ResourceMeta, SourceType
from skillens.core.scorer import score_resource
from skillens.display.i18n import resolve_lang, set_lang, t
from skillens.providers.base import BaseProvider
from skillens.providers import registry


class TestSkillDataset:
    def test_dataset_loads(self):
        data = _load()
        assert "llm" in data
        assert data["llm"].demand >= 90
        assert data["llm"].halflife_days > 0

    def test_demand_for_matches_substring(self):
        assert demand_for(["reinforcement learning"]) == 75

    def test_demand_for_title_fallback(self):
        # pytorch is in the dataset with demand=90 in the 0.2.0 refresh
        score = demand_for([], title="Intro to PyTorch")
        assert score is not None and score >= 85

    def test_demand_for_unknown(self):
        assert demand_for(["nonexistent-skill-xyz"]) is None

    def test_word_boundary_matching_rejects_substring_collisions(self):
        # "go" (golang) must NOT match inside "algorithm" / "bingo" /
        # "argo" / etc. This was a real 0.1.x bug.
        result = demand_for(["algorithm"])
        assert result != 82  # 82 was golang's demand — never should win here

    def test_halflife_picks_shortest(self):
        # A course bundling stable fundamentals (algorithms ~20y) with one
        # fast-moving tool (langchain ~180d) decays at the speed of the
        # fastest piece — the LangChain part is the bottleneck.
        hl = halflife_for(["algorithms", "langchain"])
        assert hl <= 200

    def test_halflife_default_when_unknown(self):
        hl = halflife_for(["nonexistent-skill-xyz"])
        assert hl > 0  # always returns a number, never None

    def test_scorer_uses_dataset_for_hot_skill(self):
        meta = ResourceMeta(
            title="LLM Engineering Bootcamp",
            topics=["llm", "rag"],
            source_type=SourceType.COURSE,
            platform="x",
        )
        result = score_resource(meta)
        assert result.market_demand >= 85

    def test_scorer_blends_dataset_with_popularity(self):
        meta = ResourceMeta(
            title="LLM Course",
            topics=["llm"],
            source_type=SourceType.COURSE,
            platform="x",
            enrollment_count=200_000,
        )
        result = score_resource(meta)
        # Blend of 95*0.7 + 85*0.3 = 92
        assert 88 <= result.market_demand <= 95


class FakeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "fake"

    @staticmethod
    def can_handle(url: str) -> bool:
        return url.startswith("fake://")

    async def extract(self, url: str):  # pragma: no cover
        raise NotImplementedError


class TestPluginSystem:
    def test_core_providers_registered(self):
        names = [p.__name__ for p in registry.PROVIDER_ORDER]
        assert "YouTubeProvider" in names
        assert "WebpageProvider" == names[-1]

    def test_build_order_places_webpage_last(self):
        order = registry._build_order()
        assert order[-1].__name__ == "WebpageProvider"

    def test_plugin_loader_ignores_broken(self, monkeypatch):
        class Broken:
            name = "broken"

            @classmethod
            def load(cls):
                raise RuntimeError("boom")

        monkeypatch.setattr(registry, "entry_points", lambda group: [Broken()])
        plugins = registry._load_plugins()
        assert plugins == []

    def test_plugin_loader_loads_valid(self, monkeypatch):
        class Valid:
            name = "valid"

            @classmethod
            def load(cls):
                return FakeProvider

        monkeypatch.setattr(registry, "entry_points", lambda group: [Valid()])
        plugins = registry._load_plugins()
        assert FakeProvider in plugins

    def test_plugin_ignored_if_not_provider_subclass(self, monkeypatch):
        class NotAProvider:
            pass

        class Ep:
            name = "bad"

            @classmethod
            def load(cls):
                return NotAProvider

        monkeypatch.setattr(registry, "entry_points", lambda group: [Ep()])
        assert registry._load_plugins() == []


class TestI18n:
    def teardown_method(self):
        set_lang("en")

    def test_english_default(self):
        set_lang("en")
        assert t("verdict.LEARN") == "LEARN"

    def test_chinese(self):
        set_lang("zh")
        assert t("verdict.LEARN") == "值得学"
        assert "市场需求" in t("label.market_demand")

    def test_unknown_lang_falls_to_english(self):
        set_lang("fr")
        assert t("verdict.LEARN") == "LEARN"

    def test_unknown_key_returns_key(self):
        set_lang("en")
        assert t("nonexistent.key") == "nonexistent.key"

    def test_resolve_explicit(self):
        assert resolve_lang("zh") == "zh"
        assert resolve_lang("en") == "en"

    def test_resolve_auto_from_url(self):
        assert resolve_lang("auto", "https://www.bilibili.com/video/BV1") == "zh"
        assert resolve_lang("auto", "https://youtube.com/watch?v=1") == "en"


class TestMCPBuilder:
    def test_build_server_returns_fastmcp(self):
        pytest.importorskip("mcp.server.fastmcp")
        from skillens.mcp_server import build_server

        server = build_server()
        assert server is not None
        assert hasattr(server, "run")
