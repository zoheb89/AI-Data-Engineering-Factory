import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    APP_NAME: str = os.getenv("APP_NAME","C INVENT")
    APP_VERSION: str = os.getenv("APP_VERSION","1.0.0-mvp")
    DATABASE_URL: str = os.getenv("DATABASE_URL","sqlite:///cinvent.db")
    ARTIFACT_STORE_PATH: str = os.getenv("ARTIFACT_STORE_PATH","./data/artifacts")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL","").rstrip("/")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY","")
    LLM_MODEL: str = os.getenv("LLM_MODEL","")
    LLM_AUTH_HEADER: str = os.getenv("LLM_AUTH_HEADER","Authorization")
    LLM_AUTH_SCHEME: str = os.getenv("LLM_AUTH_SCHEME","Bearer")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS","90"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS","1200"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE","0"))
    CINVENT_ALLOW_MUTATIONS: bool = os.getenv("CINVENT_ALLOW_MUTATIONS","false").lower()=="true"

settings = Settings()
