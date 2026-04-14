"""Tests for profile storage, matching, and integration with the scorer."""

import pytest

from skillens.core.models import ResourceMeta, SourceType, UserProfile
from skillens.core.scorer import score_resource
from skillens.profile import manager
from skillens.profile.matcher import match_score


@pytest.fixture
def tmp_skillens_home(tmp_path, monkeypatch):
    """Redirect ~/.skillens to a tmp dir for isolation."""
    monkeypatch.setenv("SKILLENS_HOME", str(tmp_path / ".skillens"))
    yield tmp_path


class TestProfileManager:
    def test_no_profile_by_default(self, tmp_skillens_home):
        assert manager.load_profile() is None

    def test_update_and_load(self, tmp_skillens_home):
        p = manager.update_profile(skills=["python", "pytorch"], target_role="ML engineer")
        assert p.skills == ["python", "pytorch"]
        loaded = manager.load_profile()
        assert loaded is not None
        assert loaded.target_role == "ML engineer"

    def test_merge_preserves_existing(self, tmp_skillens_home):
        manager.update_profile(skills=["python"])
        manager.update_profile(target_role="SRE")
        loaded = manager.load_profile()
        assert loaded.skills == ["python"]
        assert loaded.target_role == "SRE"

    def test_clear(self, tmp_skillens_home):
        manager.update_profile(skills=["rust"])
        manager.clear_profile()
        assert manager.load_profile() is None


class TestMatcher:
    def _meta(self, **kw):
        defaults = {"title": "Test", "source_type": SourceType.COURSE, "platform": "x"}
        defaults.update(kw)
        return ResourceMeta(**defaults)

    def test_no_profile_tokens_returns_neutral(self):
        meta = self._meta(topics=["python"])
        profile = UserProfile()
        assert match_score(meta, profile) == 50

    def test_sweet_spot_overlap_scores_high(self):
        meta = self._meta(
            title="Reinforcement Learning with PyTorch",
            topics=["policy gradient", "actor critic", "ppo", "dqn", "tabular", "monte carlo"],
        )
        profile = UserProfile(skills=["pytorch"])
        score = match_score(meta, profile)
        assert score >= 60

    def test_heavy_overlap_is_penalized_as_redundant(self):
        meta = self._meta(title="python", topics=["python"])
        profile = UserProfile(skills=["python"])
        assert match_score(meta, profile) <= 80  # not above sweet-spot

    def test_role_bonus_applies(self):
        meta = self._meta(title="Kubernetes Basics", topics=["kubernetes"])
        profile = UserProfile(
            skills=["docker", "linux", "terraform", "aws"],
            target_role="kubernetes SRE",
        )
        assert match_score(meta, profile) > 40


class TestScorerProfileIntegration:
    def test_profile_match_attached_when_profile_exists(self, tmp_skillens_home):
        manager.update_profile(skills=["python", "pytorch"])
        meta = ResourceMeta(
            title="Deep Learning with PyTorch",
            topics=["pytorch", "neural networks"],
            source_type=SourceType.COURSE,
            platform="test",
        )
        result = score_resource(meta)
        assert result.profile_match is not None

    def test_no_profile_match_when_no_profile(self, tmp_skillens_home):
        meta = ResourceMeta(title="Anything", source_type=SourceType.COURSE, platform="x")
        result = score_resource(meta)
        assert result.profile_match is None
