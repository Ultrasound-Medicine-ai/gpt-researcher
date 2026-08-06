import os

import pytest

from gpt_researcher.retrievers.tavily.key_pool import (
    get_current_tavily_key,
    get_tavily_keys,
    mark_tavily_key_exhausted,
    reload_tavily_keys,
    should_rotate_tavily_key,
    with_tavily_key_rotation,
)


@pytest.fixture(autouse=True)
def reset_key_pool(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEYS", raising=False)
    reload_tavily_keys()
    yield
    reload_tavily_keys()


def test_load_multiple_keys_from_env(monkeypatch):
    monkeypatch.setenv(
        "TAVILY_API_KEYS",
        "tvly-dev-key-one,tvly-dev-key-two",
    )
    reload_tavily_keys()

    assert get_tavily_keys() == ["tvly-dev-key-one", "tvly-dev-key-two"]
    assert get_current_tavily_key() == "tvly-dev-key-one"


def test_fallback_to_single_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-dev-single")
    reload_tavily_keys()

    assert get_tavily_keys() == ["tvly-dev-single"]


def test_mark_key_exhausted_switches_to_next(monkeypatch):
    monkeypatch.setenv(
        "TAVILY_API_KEYS",
        "tvly-dev-key-one,tvly-dev-key-two",
    )
    reload_tavily_keys()

    mark_tavily_key_exhausted("tvly-dev-key-one", reason="plan limit")

    assert get_tavily_keys() == ["tvly-dev-key-two"]
    assert get_current_tavily_key() == "tvly-dev-key-two"


def test_should_rotate_on_plan_limit_status_codes():
    assert should_rotate_tavily_key(status_code=432, error_message="plan limit")
    assert should_rotate_tavily_key(status_code=401, error_message="invalid key")


def test_with_tavily_key_rotation_switches_on_quota_error(monkeypatch):
    monkeypatch.setenv(
        "TAVILY_API_KEYS",
        "tvly-dev-key-one,tvly-dev-key-two",
    )
    reload_tavily_keys()

    calls: list[str] = []

    class PlanLimitError(Exception):
        pass

    def operation(api_key: str) -> str:
        calls.append(api_key)
        if api_key == "tvly-dev-key-one":
            raise PlanLimitError("This request exceeds your plan's set usage limit.")
        return "ok"

    result = with_tavily_key_rotation(operation)

    assert result == "ok"
    assert calls == ["tvly-dev-key-one", "tvly-dev-key-two"]


def test_with_tavily_key_rotation_raises_when_all_keys_fail(monkeypatch):
    monkeypatch.setenv(
        "TAVILY_API_KEYS",
        "tvly-dev-key-one,tvly-dev-key-two",
    )
    reload_tavily_keys()

    def operation(api_key: str) -> str:
        raise RuntimeError("This request exceeds your plan's set usage limit.")

    with pytest.raises(RuntimeError):
        with_tavily_key_rotation(operation)

    assert get_tavily_keys() == []
