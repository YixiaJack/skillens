"""Provider URL-detection tests (no network)."""

from skillens.providers.arxiv import ArXivProvider
from skillens.providers.github_repo import GitHubRepoProvider
from skillens.providers.registry import detect_provider
from skillens.providers.webpage import WebpageProvider
from skillens.providers.youtube import YouTubeProvider


class TestYouTube:
    def test_watch_url(self):
        assert YouTubeProvider.can_handle("https://www.youtube.com/watch?v=abc123")

    def test_short_url(self):
        assert YouTubeProvider.can_handle("https://youtu.be/abc123")

    def test_shorts_url(self):
        assert YouTubeProvider.can_handle("https://youtube.com/shorts/xyz")

    def test_rejects_non_youtube(self):
        assert not YouTubeProvider.can_handle("https://example.com/watch?v=abc")


class TestGitHub:
    def test_repo_url(self):
        assert GitHubRepoProvider.can_handle("https://github.com/openai/gym")

    def test_repo_with_git_suffix(self):
        assert GitHubRepoProvider.can_handle("https://github.com/openai/gym.git")

    def test_rejects_features_page(self):
        assert not GitHubRepoProvider.can_handle("https://github.com/features")

    def test_rejects_non_github(self):
        assert not GitHubRepoProvider.can_handle("https://gitlab.com/foo/bar")


class TestArXiv:
    def test_abs_url(self):
        assert ArXivProvider.can_handle("https://arxiv.org/abs/2301.00001")

    def test_pdf_url(self):
        assert ArXivProvider.can_handle("https://arxiv.org/pdf/2301.00001v2")

    def test_rejects_non_arxiv(self):
        assert not ArXivProvider.can_handle("https://example.org/abs/2301.00001")


class TestWebpageFallback:
    def test_accepts_any_http(self):
        assert WebpageProvider.can_handle("https://blog.example.com/post")

    def test_rejects_non_http(self):
        assert not WebpageProvider.can_handle("ftp://example.com/file")


class TestRegistry:
    def test_youtube_wins_over_webpage(self):
        p = detect_provider("https://www.youtube.com/watch?v=abc")
        assert p.name == "youtube"

    def test_github_wins_over_webpage(self):
        p = detect_provider("https://github.com/openai/gym")
        assert p.name == "github"

    def test_arxiv_detected(self):
        p = detect_provider("https://arxiv.org/abs/2301.00001")
        assert p.name == "arxiv"

    def test_unknown_falls_to_webpage(self):
        p = detect_provider("https://example.com/some-article")
        assert p.name == "webpage"
