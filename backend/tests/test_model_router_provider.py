"""Provider-Wahl (`HV_LLM_PROVIDER`) + der austauschbare `MistralLLMClient`
(§12/NFR-5: austauschbarer LLM-Anbieter, rein per Konfiguration)."""

from unittest.mock import MagicMock

import pytest

from app.agent.demo_llm_client import DemoLLMClient
from app.agent.model_router import AnthropicLLMClient, MistralLLMClient, _default_client
from app.config import settings


@pytest.fixture(autouse=True)
def _settings_zuruecksetzen():
    """Verhindert, dass Provider-Overrides aus diesem Test in andere Tests
    durchsickern (settings ist ein Modul-Singleton)."""
    ursprung = (settings.llm_provider, settings.anthropic_api_key, settings.mistral_api_key)
    yield
    settings.llm_provider, settings.anthropic_api_key, settings.mistral_api_key = ursprung


def test_explizite_wahl_mistral():
    settings.llm_provider = "mistral"
    assert isinstance(_default_client(), MistralLLMClient)


def test_explizite_wahl_anthropic():
    settings.llm_provider = "anthropic"
    assert isinstance(_default_client(), AnthropicLLMClient)


def test_explizite_wahl_demo():
    settings.llm_provider = "demo"
    settings.anthropic_api_key = "irrelevant-bei-expliziter-wahl"
    assert isinstance(_default_client(), DemoLLMClient)


def test_ohne_provider_wahl_aber_anthropic_key_verwendet_anthropic():
    settings.llm_provider = None
    settings.anthropic_api_key = "sk-test"
    assert isinstance(_default_client(), AnthropicLLMClient)


def test_ohne_provider_wahl_und_ohne_key_verwendet_demo():
    settings.llm_provider = None
    settings.anthropic_api_key = None
    settings.mistral_api_key = None
    assert isinstance(_default_client(), DemoLLMClient)


def test_mistral_client_sendet_system_und_user_nachricht():
    client = MistralLLMClient()
    fake_antwort = MagicMock()
    fake_antwort.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    client._client = MagicMock()
    client._client.chat.complete.return_value = fake_antwort

    antwort = client.complete("mistral-small-latest", "System", "User", temperature=0.0)

    assert antwort.text == '{"ok": true}'
    assert antwort.modell == "mistral-small-latest"
    client._client.chat.complete.assert_called_once_with(
        model="mistral-small-latest",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User"},
        ],
        timeout_ms=25_000,
    )
