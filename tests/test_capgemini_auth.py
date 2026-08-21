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
        max_tokens=100,
        temperature=0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_x_api_key_default():
    assert CapgeminiLLM(settings())._headers()["x-api-key"] == "abc123"


def test_bearer_authorization():
    h = CapgeminiLLM(settings(llm_auth_header="Authorization", llm_auth_scheme="bearer"))._headers()
    assert h["Authorization"] == "Bearer abc123"


def test_api_key_header():
    h = CapgeminiLLM(settings(llm_auth_header="api-key"))._headers()
    assert h["api-key"] == "abc123"
