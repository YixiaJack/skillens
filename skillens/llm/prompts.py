"""Prompt builders for LLM analysis."""

from __future__ import annotations

from skillens.core.models import ResourceMeta


def build_analysis_prompt(meta: ResourceMeta) -> str:
    """Build the deep-analysis prompt from resource metadata."""
    parts = [
        f"Resource: {meta.title}",
        f"Platform: {meta.platform}",
        f"Source type: {meta.source_type.value}",
    ]
    if meta.author:
        parts.append(f"Author: {meta.author}")
    if meta.institution:
        parts.append(f"Institution: {meta.institution}")
    if meta.published_date:
        parts.append(f"Published: {meta.published_date.strftime('%Y-%m-%d')}")
    if meta.last_updated:
        parts.append(f"Last updated: {meta.last_updated.strftime('%Y-%m-%d')}")
    if meta.duration_hours:
        parts.append(f"Duration: {meta.duration_hours:.1f} hours")
    if meta.rating:
        parts.append(f"Rating: {meta.rating}/5")
    if meta.enrollment_count:
        parts.append(f"Enrollment: {meta.enrollment_count}")
    if meta.star_count:
        parts.append(f"GitHub stars: {meta.star_count}")
    if meta.topics:
        parts.append(f"Topics: {', '.join(meta.topics)}")
    if meta.syllabus:
        parts.append("Syllabus:\n- " + "\n- ".join(meta.syllabus[:20]))
    if meta.description:
        parts.append(f"Description: {meta.description}")
    if meta.content_sample:
        parts.append(f"Content sample:\n{meta.content_sample[:1500]}")

    parts.append(
        "\nEvaluate on these dimensions (each 0-100):\n"
        "- market_demand: value in current job market\n"
        "- info_density: useful, non-redundant content density\n"
        "- freshness: up-to-date with current best practices\n"
        "- effort_vs_return: is the time investment justified?\n"
        "\nAlso provide 2-3 strengths, 2-3 concerns, 2-3 alternative resources, "
        "and a one-line verdict_reason."
    )
    return "\n".join(parts)
