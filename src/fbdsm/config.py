from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import mlflow

class Settings(BaseSettings):
    KNOWUNITY_API_KEY: str
    OPENAI_API_KEY: str
    OPENROUTER_API_KEY: str
    MODEL_NAME: str
    MLFLOW_TRACING:bool
    KNOWUNITY_API_URL: str = "https://knowunity-agent-olympics-2026-api.vercel.app"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

print("Model name: ", settings.MODEL_NAME)

os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

mlflow.pydantic_ai.autolog(log_traces=settings.MLFLOW_TRACING)