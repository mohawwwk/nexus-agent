import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    upload_dir: str = "uploads"
    max_file_size_mb: int = 50
    model_name: str = "llama-3.3-70b-versatile"
    whisper_model: str = "whisper-large-v3"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings(groq_api_key=os.environ.get("GROQ_API_KEY", ""))
