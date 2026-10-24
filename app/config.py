from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    model_id: str = "claude-sonnet-5"
    log_level: str = "INFO"
    max_tokens: int = 4096


settings = Settings()
