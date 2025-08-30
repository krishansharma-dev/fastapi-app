from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://postgres:password@db:5432/fastapi_db"
    db_host: str = "db"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "password"
    db_name: str = "fastapi_db"
    
    # Redis settings
    redis_url: str = "redis://redis:6379/0"
    redis_host: str = "redis"
    redis_port: int = 6379
    
    # Application settings
    secret_key: str = "your-secret-key-here"
    debug: bool = True
    app_port: int = 8000
    
    class Config:
        env_file = ".env"


settings = Settings()
