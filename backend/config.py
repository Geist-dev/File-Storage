from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / '.env', extra='ignore')

    APP_NAME: str = 'File Storage'
    APP_HOST: str = '127.0.0.1'
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    JWT_SECRET: str = Field(min_length=32)
    JWT_EXPIRES_MIN: int = Field(default=60 * 24, ge=1)
    STORAGE_DIR: Path = BACKEND_DIR / '.data' / 'storage'
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / '.data' / 'data.db'}"
    MAX_UPLOAD_MB: int = Field(default=50, ge=1)
    ALLOWED_MIME: str = 'image/jpeg,image/png,image/webp,application/pdf,text/plain'

    @field_validator('JWT_SECRET')
    @classmethod
    def reject_example_secret(cls, value):
        if value.startswith(('change_me', 'REPLACE_')):
            raise ValueError('Generate a private JWT_SECRET with: python scripts/setup_env.py')
        return value

    @field_validator('STORAGE_DIR')
    @classmethod
    def resolve_storage(cls, value):
        return value if value.is_absolute() else BACKEND_DIR / value

    @field_validator('DATABASE_URL')
    @classmethod
    def resolve_database(cls, value):
        prefix = 'sqlite:///'
        if value.startswith(prefix):
            location = value[len(prefix):]
            if location != ':memory:' and not Path(location).is_absolute():
                return prefix + str(BACKEND_DIR / location)
        return value


settings = Settings()
