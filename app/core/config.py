from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  

    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_NAME: str = "intel_platform_session"

    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_HOST: str = "http://localhost:11434"

    GEONAMES_USERNAME: str

    class Config:
        env_file = ".env"

settings = Settings()