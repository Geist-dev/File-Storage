from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "FileStoragePython"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    JWT_SECRET: str = Field(default="change_me", min_length=8)
    JWT_EXPIRES_MIN: int = 60 * 24 * 7

    STORAGE_DIR: str = "storage"
    DATABASE_URL: str = "sqlite:///./data.db"

    MAX_UPLOAD_MB: int = 50
    ALLOWED_MIME: str = "image/jpeg,image/png,image/webp,application/pdf,text/plain"

    class Config:
        env_file = ".env"

settings = Settings()
