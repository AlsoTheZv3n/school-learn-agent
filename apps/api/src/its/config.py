from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    data_mode: str = "mock"
    min_cohort_k: int = 10
    llm_backend: str = "local"
    llm_api_key: str | None = None
    jwt_public_key: str | None = None


settings = Settings()  # type: ignore[call-arg]
