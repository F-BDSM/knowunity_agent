from pydantic_settings import BaseSettings, SettingsConfigDict
import dspy

class Settings(BaseSettings):
    KNOWUNITY_API_KEY: str
    OPENAI_API_KEY: str
    LLM_API_URL: str
    MODEL_NAME: str
    KNOWUNITY_API_URL: str = "https://knowunity-agent-olympics-2026-api.vercel.app"
    
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

lm = dspy.LM(model=settings.MODEL_NAME, api_key=settings.OPENAI_API_KEY,api_base=settings.LLM_API_URL)
dspy.configure(lm=lm)