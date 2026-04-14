"""Tests for config storage."""

import pytest

from skillens.core import config


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLENS_HOME", str(tmp_path / ".skillens"))
    yield


def test_empty_by_default(tmp_home):
    assert config.load_config() == {}


def test_set_and_get(tmp_home):
    config.set_value("llm", "ollama")
    config.set_value("model", "llama3.2")
    cfg = config.load_config()
    assert cfg["llm"] == "ollama"
    assert cfg["model"] == "llama3.2"


def test_hyphen_key_normalized(tmp_home):
    config.set_value("api-key", "sk-abc")
    assert config.get_value("api_key") == "sk-abc"


def test_factory_returns_ollama(tmp_home):
    config.set_value("llm", "ollama")
    from skillens.llm.factory import get_backend
    from skillens.llm.ollama import OllamaBackend

    assert isinstance(get_backend(), OllamaBackend)


def test_factory_defaults_to_openai(tmp_home):
    from skillens.llm.factory import get_backend
    from skillens.llm.openai import OpenAIBackend

    assert isinstance(get_backend(), OpenAIBackend)
