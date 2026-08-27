
from dataclasses import dataclass
import os, yaml

@dataclass
class Settings:
    llm_base_url:str
    llm_model:str
    llm_provider:str
    llm_api_key:str
    llm_protocol:str
    llm_interface:str
    llm_mode:str
    llm_auth_header:str
    llm_auth_scheme:str
    temperature:float
    max_tokens:int
    llm_timeout_seconds:int
    db_host:str
    db_token:str
    db_warehouse_id:str
    allow_mutations:bool
    image_base_url:str
    image_model:str
    image_provider:str
    image_api_key:str
    app_name:str
    app_version:str

def _secret(name,default=""):
    try:
        import streamlit as st
        return st.secrets.get(name,os.getenv(name,default))
    except Exception: return os.getenv(name,default)
def _bool(v): return str(v).lower() in {"1","true","yes","on"}

def load_settings():
    cfg={}
    for candidate in ("config.yaml", os.path.join(os.path.dirname(__file__),"../../config.yaml")):
        try:
            with open(os.path.abspath(candidate),"r",encoding="utf-8") as f:
                cfg=yaml.safe_load(f) or {}
                break
        except Exception:
            continue
    llm=cfg.get("llm",{}); db=cfg.get("databricks",{}); app=cfg.get("app",{}); image=cfg.get("image",{})
    return Settings(
      _secret("LLM_ENDPOINT",llm.get("base_url","")),
      _secret("LLM_MODEL",llm.get("model_name","")),
      _secret("LLM_PROVIDER",llm.get("provider","")),
      _secret("LLM_API_KEY",""),
      _secret("LLM_PROTOCOL",llm.get("protocol","auto")),
      llm.get("model_interface","generic"),llm.get("mode","chat"),
      _secret("LLM_AUTH_HEADER",llm.get("auth_header","Authorization")),
      _secret("LLM_AUTH_SCHEME",llm.get("auth_scheme","Bearer")),
      float(_secret("LLM_TEMPERATURE",llm.get("temperature",0.0))),
      int(_secret("LLM_MAX_TOKENS",llm.get("max_tokens",1200))),
      int(_secret("LLM_TIMEOUT_SECONDS",llm.get("timeout_seconds",90))),
      _secret("DATABRICKS_HOST",""),_secret("DATABRICKS_TOKEN",""),_secret("DATABRICKS_WAREHOUSE_ID",""),
      _bool(_secret("ALLOW_MUTATIONS",db.get("allow_mutations",False))),
      _secret("IMAGE_ENDPOINT",image.get("base_url","")),_secret("IMAGE_MODEL",image.get("model_name","")),
      _secret("IMAGE_PROVIDER",image.get("provider","")),_secret("IMAGE_API_KEY",""),
      app.get("name","EliteInteliA Intelligence Factory"),app.get("version","1.0.0")
    )
