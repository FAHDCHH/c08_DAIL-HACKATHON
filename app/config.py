from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://evidence:change_me@db:5432/evidence"

    # provider: deepseek (OpenAI-compatible) | anthropic
    agent_provider: str = "deepseek"
    agent_mode: str = "live"  # live | mock
    agent_model: str = "deepseek-chat"

    # deepseek / any OpenAI-compatible endpoint
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # anthropic (kept as an alternate provider)
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""

    contexts_dir: str = "contexts"
    scenarios_dir: str = "scenarios"
    reports_dir: str = "reports_out"


settings = Settings()
