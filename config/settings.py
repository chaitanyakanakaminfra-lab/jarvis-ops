from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    jarvis_env: str = Field(default="development")
    jarvis_log_level: str = Field(default="INFO")
    jarvis_api_port: int = Field(default=8000)
    jarvis_voice_enabled: bool = Field(default=True)
    jarvis_wake_word: str = Field(default="jarvis")

    # Groq
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # Voice
    porcupine_access_key: str = Field(...)
    deepgram_api_key: str = Field(...)
    elevenlabs_api_key: str = Field(...)
    elevenlabs_voice_id: str = Field(...)

    # GitHub
    github_token: str = Field(...)
    github_org: str = Field(...)
    github_repo: str = Field(...)

    # AWS
    aws_access_key_id: str = Field(...)
    aws_secret_access_key: str = Field(...)
    aws_default_region: str = Field(default="us-east-1")
    aws_account_id: str = Field(...)
    ecr_registry: str = Field(...)

    # Argo
    argo_server_url: str = Field(...)
    argo_token: str = Field(...)
    argo_namespace: str = Field(default="jarvis")

    # Database
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="jarvis")
    postgres_user: str = Field(default="jarvis")
    postgres_password: str = Field(...)
    database_url: str = Field(...)

    # ChromaDB
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8001)

    @property
    def is_production(self) -> bool:
        return self.jarvis_env == "production"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
