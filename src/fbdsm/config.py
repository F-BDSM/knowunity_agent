from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import ChatOpenAI

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

# Strip provider prefix if present (e.g., "openai/x-ai/grok-4-fast" -> "x-ai/grok-4-fast")
model_name = settings.MODEL_NAME
if model_name.startswith("openai/"):
    model_name = model_name[7:]  # Remove "openai/" prefix

llm = ChatOpenAI(
    model=model_name,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.LLM_API_URL,
)
