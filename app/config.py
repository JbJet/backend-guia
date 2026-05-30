from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv('GEMINI_API_KEY')
    ocr_confidence_threshold: float = 0.6

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
