"""Coursera provider tests — JSON-LD parsing and URL detection."""

import pytest
import respx
from httpx import Response

from skillens.providers.coursera import CourseraProvider

SAMPLE_HTML = """
<html><head>
<title>Machine Learning | Coursera</title>
<meta property="og:title" content="Machine Learning — Stanford">
<meta property="og:description" content="Learn ML from Andrew Ng.">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Machine Learning",
  "description": "Foundations of machine learning from Stanford.",
  "provider": {"@type": "Organization", "name": "Stanford University"},
  "instructor": [{"@type": "Person", "name": "Andrew Ng"}],
  "aggregateRating": {"ratingValue": "4.9", "ratingCount": 180000},
  "keywords": "machine learning, regression, neural networks",
  "datePublished": "2012-10-15",
  "dateModified": "2024-03-01",
  "timeRequired": "PT60H",
  "teaches": [
    {"@type": "DefinedTerm", "name": "Linear Regression"},
    {"@type": "DefinedTerm", "name": "Logistic Regression"}
  ]
}
</script>
</head><body>
<h3>Module 1: Linear Regression</h3>
<p>1,234,567 already enrolled</p>
</body></html>
"""

SAMPLE_HTML_NO_KEYWORDS_WITH_SKILLS_SECTION = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "Data Structures",
  "provider": {"@type": "Organization", "name": "UCSD"},
  "aggregateRating": {"ratingValue": "4.5", "ratingCount": 5000},
  "timeRequired": "PT1H30M"
}
</script>
</head><body>
<h3>Skills you'll gain</h3>
<ul>
  <li>Hash Tables</li>
  <li>Binary Trees</li>
  <li>Graph Algorithms</li>
</ul>
<p>45K already enrolled</p>
</body></html>
"""


class TestCourseraDetection:
    def test_learn_url(self):
        assert CourseraProvider.can_handle(
            "https://www.coursera.org/learn/machine-learning"
        )

    def test_specialization_url(self):
        assert CourseraProvider.can_handle(
            "https://www.coursera.org/specializations/deep-learning"
        )

    def test_rejects_non_coursera(self):
        assert not CourseraProvider.can_handle("https://example.com/learn/foo")


class TestCourseraExtraction:
    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_json_ld(self):
        url = "https://www.coursera.org/learn/machine-learning"
        respx.get(url).mock(return_value=Response(200, html=SAMPLE_HTML))

        meta = await CourseraProvider().extract(url)

        assert meta.title == "Machine Learning"
        assert meta.platform == "coursera"
        assert meta.institution == "Stanford University"
        assert "Andrew Ng" in meta.author
        assert meta.rating == 4.9
        assert meta.review_count == 180000
        assert "machine learning" in meta.topics
        assert meta.published_date is not None
        assert meta.last_updated is not None
        # 0.2.0: duration via ISO 8601 timeRequired
        assert meta.duration_hours == 60.0
        # 0.2.0: enrollment from "1,234,567 already enrolled" text
        assert meta.enrollment_count == 1_234_567
        # 0.2.0: topics include teaches entries
        assert any("regression" in t.lower() for t in meta.topics)

    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_skills_section_when_no_keywords(self):
        url = "https://www.coursera.org/learn/data-structures"
        respx.get(url).mock(
            return_value=Response(200, html=SAMPLE_HTML_NO_KEYWORDS_WITH_SKILLS_SECTION)
        )
        meta = await CourseraProvider().extract(url)
        # Should find "Hash Tables" / "Binary Trees" / "Graph Algorithms" from
        # the "Skills you'll gain" section
        assert len(meta.topics) >= 1
        # PT1H30M = 1.5 hours
        assert meta.duration_hours == 1.5
        # "45K already enrolled" → 45000
        assert meta.enrollment_count == 45_000


class TestISODurationParser:
    def test_pt60h(self):
        from skillens.providers.coursera import _parse_iso_duration_hours
        assert _parse_iso_duration_hours("PT60H") == 60.0

    def test_pt1h30m(self):
        from skillens.providers.coursera import _parse_iso_duration_hours
        assert _parse_iso_duration_hours("PT1H30M") == 1.5

    def test_p7d(self):
        from skillens.providers.coursera import _parse_iso_duration_hours
        assert _parse_iso_duration_hours("P7D") == 168.0

    def test_invalid(self):
        from skillens.providers.coursera import _parse_iso_duration_hours
        assert _parse_iso_duration_hours("not a duration") is None
        assert _parse_iso_duration_hours("") is None
