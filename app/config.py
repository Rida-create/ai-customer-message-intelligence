import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "AI Customer Message Intelligence System")
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")


settings = Settings()