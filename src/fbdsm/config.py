from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    KNOWUNITY_API_KEY: str
    #OPENAI_API_KEY: str
    #LLM_API_URL: str
    OPENROUTER_API_KEY: str
    MODEL_NAME: str
    KNOWUNITY_API_URL: str = "https://knowunity-agent-olympics-2026-api.vercel.app"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY