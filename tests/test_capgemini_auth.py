from types import SimpleNamespace
from c_invent.llm.capgemini import CapgeminiLLM


def settings(**overrides):
    base = dict(
        llm_api_key="abc123",
        llm_auth_header="x-api-key",
        llm_auth_scheme="none",
        llm_base_url="https://example.test",
        llm_model="openai.gpt-5.1",
        llm_provider="azure",
        llm_interface="langchain",
        llm_mode="chain",
        capgemini_workspace_id="workspace",
        max_tokens=1200,
        temperature=0.1,
        llm_timeout_seconds=90,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_x_api_key_default():
    assert CapgeminiLLM(settings())._headers()["x-api-key"] == "abc123"


def test_bearer_authorization():
    h = CapgeminiLLM(settings(llm_auth_header="Authorization", llm_auth_scheme="bearer"))._headers()
    assert h["Authorization"] == "Bearer abc123"


def test_capgemini_payload_contract():
    p = CapgeminiLLM(settings())._payload("hello", "system")
    assert p["action"] == "run"
    assert p["modelInterface"] == "langchain"
    assert isinstance(p["data"], dict)
    d = p["data"]
    assert d["mode"] == "chain"
    assert d["modelName"] == "openai.gpt-5.1"
    assert d["provider"] == "azure"
    assert "workspaceId" not in d
    assert "modelKwargs" in d
    assert d["modelKwargs"]["streaming"] is False
    assert "modelParams" not in p
    assert "data" not in ("", None)
