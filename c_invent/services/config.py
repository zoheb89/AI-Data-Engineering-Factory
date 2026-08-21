from dataclasses import dataclass
import os
import yaml


@dataclass
class Settings:
    llm_base_url: str
    llm_model: str
    llm_provider: str
    llm_api_key: str
    capgemini_workspace_id: str
    include_workspace_id: bool
    llm_interface: str
    llm_mode: str
    llm_auth_header: str
    llm_auth_scheme: str
    temperature: float
    max_tokens: int
    llm_timeout_seconds: int
    db_host: str
    db_token: str
    db_warehouse_id: str
    allow_mutations: bool
    image_base_url: str
    image_model: str
    image_provider: str
    image_api_key: str
    app_name: str
    app_version: str


def _secret(name, default=""):
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


def _bool(v):
    return str(v).lower() in {"1", "true", "yes", "on"}


def load_settings():
    cfg = {}
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        pass

    llm = cfg.get("llm", {})
    db = cfg.get("databricks", {})
    app = cfg.get("app", {})
    image = cfg.get("image", {})

    return Settings(
        llm_base_url=_secret("CAPGEMINI_LLM_BASE_URL", llm.get("base_url", "")),
        llm_model=_secret("CAPGEMINI_LLM_MODEL", llm.get("model_name", "openai.gpt-5.1")),
        llm_provider=_secret("CAPGEMINI_LLM_PROVIDER", llm.get("provider", "azure")),
        llm_api_key=_secret("CAPGEMINI_LLM_API_KEY", ""),
        capgemini_workspace_id=_secret("CAPGEMINI_WORKSPACE_ID", ""),
        include_workspace_id=_bool(_secret("CAPGEMINI_INCLUDE_WORKSPACE_ID", "false")),
        llm_interface=llm.get("model_interface", "langchain"),
        llm_mode=llm.get("mode", "chain"),
        llm_auth_header=_secret(
            "CAPGEMINI_LLM_AUTH_HEADER", llm.get("auth_header", "x-api-key")
        ),
        llm_auth_scheme=_secret(
            "CAPGEMINI_LLM_AUTH_SCHEME", llm.get("auth_scheme", "none")
        ),
        temperature=float(llm.get("temperature", 0)),
        max_tokens=int(llm.get("max_tokens", 1200)),
        llm_timeout_seconds=int(_secret("LLM_TIMEOUT_SECONDS", "90")),
        db_host=_secret("DATABRICKS_HOST", ""),
        db_token=_secret("DATABRICKS_TOKEN", ""),
        db_warehouse_id=_secret("DATABRICKS_WAREHOUSE_ID", ""),
        allow_mutations=_bool(
            _secret("CINVENT_ALLOW_MUTATIONS", db.get("allow_mutations", False))
        ),
        image_base_url=_secret("CAPGEMINI_IMAGE_BASE_URL", image.get("base_url", "")),
        image_model=_secret("CAPGEMINI_IMAGE_MODEL", image.get("model_name", "")),
        image_provider=_secret("CAPGEMINI_IMAGE_PROVIDER", image.get("provider", "")),
        image_api_key=_secret("CAPGEMINI_IMAGE_API_KEY", ""),
        app_name=app.get("name", "C INVENT"),
        app_version=app.get("version", "0.1.0-poc"),
    )
