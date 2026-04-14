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
  "dateModified": "2024-03-01"
}
</script>
</head><body><h3>Module 1: Linear Regression</h3></body></html>
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
