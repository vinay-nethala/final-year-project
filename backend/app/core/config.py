from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Based Expiry-Aware Dynamic Discount System"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite:///./discount_system.db"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    RL_MODEL_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rl", "trained_policy.json")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
