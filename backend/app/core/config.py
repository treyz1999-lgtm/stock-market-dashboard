'''Environment-backed application configuration.'''

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    '''Settings required to connect to the Twelve Data API.'''

    TWELVE_DATA_API_KEY: str
    TWELVE_DATA_BASE_URL: str

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


settings = Settings()
