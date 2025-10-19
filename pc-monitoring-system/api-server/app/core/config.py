from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost/pc_monitoring"
    
    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_title: str = "PC Monitoring API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Agent
    agent_scan_interval_minutes: int = 1440  # 24 horas
    agent_auto_start: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()