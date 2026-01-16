from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    KNOWUNITY_API_KEY: str
    KNOWUNITY_API_URL: str = "https://knowunity-agent-olympics-2026-api.vercel.app"
    OPENAI_API_KEY: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()