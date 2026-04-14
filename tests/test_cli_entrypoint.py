"""Regression test for the bare-URL CLI invocation.

Guards against the 0.1.0 bug where `skillens "https://..."` failed with
`No such command 'https://...'` because the pyproject entry point was
pointing at `app` (which bypasses the argv rewriting in `main`).
"""

from __future__ import annotations

import sys

import pytest


def test_entrypoint_is_main_not_app():
    """The pyproject console_script must target main(), not app().

    main() rewrites sys.argv to inject 'evaluate' before any URL arg,
    so `skillens "https://..."` works without an explicit subcommand.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        import importlib_metadata as importlib_metadata  # type: ignore
        entry_points = importlib_metadata.entry_points  # type: ignore

    scripts = entry_points(group="console_scripts")
    skillens_eps = [ep for ep in scripts if ep.name == "skillens"]
    if not skillens_eps:
        pytest.skip("skillens console_script not installed in this env")
    ep = skillens_eps[0]
    assert ep.value.endswith(":main"), (
        f"Entry point must target skillens.cli:main so bare-URL injection "
        f"runs. Got: {ep.value}"
    )


def test_main_injects_evaluate_before_url(monkeypatch):
    """Calling main() with a bare URL must insert 'evaluate' into argv."""
    from skillens import cli

    captured: dict = {}

    def fake_app():
        captured["argv"] = list(sys.argv)

    monkeypatch.setattr(cli, "app", fake_app)
    monkeypatch.setattr(
        sys,
        "argv",
        ["skillens", "https://www.coursera.org/learn/machine-learning"],
    )
    cli.main()
    assert captured["argv"][1] == "evaluate"
    assert captured["argv"][2] == "https://www.coursera.org/learn/machine-learning"


def test_main_does_not_inject_for_known_command(monkeypatch):
    """Subcommands like `profile show` must pass through untouched."""
    from skillens import cli

    captured: dict = {}

    def fake_app():
        captured["argv"] = list(sys.argv)

    monkeypatch.setattr(cli, "app", fake_app)
    monkeypatch.setattr(sys, "argv", ["skillens", "profile", "show"])
    cli.main()
    assert captured["argv"][1] == "profile"
