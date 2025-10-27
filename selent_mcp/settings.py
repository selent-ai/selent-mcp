from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")  # pyright: ignore[reportUnannotatedClassAttribute]

    # Single API key (backward compatible) or comma-separated multiple keys
    # Format: "key1" or "key1,key2,key3"
    # Optional naming format: "name1:key1,name2:key2"
    MERAKI_API_KEY: str = ""

    SELENT_API_KEY: str = ""
    SELENT_API_BASE_URL: str = "https://backend.selent.ai"
