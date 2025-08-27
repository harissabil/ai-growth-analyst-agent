from functools import lru_cache

from pydantic import AnyUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    azure_openai_endpoint: AnyUrl = Field(alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: SecretStr = Field(alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(alias="AZURE_OPENAI_API_VERSION")

    data_service_base_url: AnyUrl = Field(alias="DATA_SERVICE_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
