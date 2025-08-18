from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    MERAKI_API_KEY: str = ""
    SELENT_API_KEY: str = ""
    SELENT_API_BASE_URL: str = "https://backend.selent.ai"
