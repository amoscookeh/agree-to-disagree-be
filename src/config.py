from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    openrouter_api_key: str = "your_key_here"
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_site_name: str = "AgreeToDisagree"

    supabase_url: str = "your_supabase_url"
    supabase_key: str = "your_supabase_key"
    supabase_anon_key: str = ""
    database_url: str = ""

    nyt_api_key: str = ""
    guardian_api_key: str = ""
    newsapi_key: str = ""
    semantic_scholar_api_key: str = ""
    serpapi_key: str = ""

    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
