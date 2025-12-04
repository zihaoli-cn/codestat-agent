"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "CodeStat Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/codestat.db"
    
    # Storage
    data_dir: str = "./data"
    
    # Task scheduler
    task_check_interval: int = 5  # seconds
    task_max_memory: int = 1000  # max tasks to keep in memory
    task_cleanup_age_hours: int = 24
    
    # Container
    worker_image: str = "codestat-worker:latest"
    container_memory_limit: str = "512m"
    container_cpu_quota: int = 50000  # 50% of one core
    
    # Default CLOC config
    default_cloc_timeout: int = 600  # seconds
    default_cloc_output_format: str = "json"
    default_use_gitignore: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
