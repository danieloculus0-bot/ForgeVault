from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the ForgeVault API."""

    database_url: str = "postgresql+psycopg://forgevault:forgevault@localhost:5432/forgevault"
    local_vault_root: str = "./data/vault"
    staging_root: str = "./data/staging"
    service_name: str = "forgevault-api"
    auto_create_schema: bool = False
    jobboss2_outbox_root: str = "./data/jobboss2/outbox"
    jobboss2_webhook_url: str | None = None
    jobboss2_api_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="FORGEVAULT_", env_file=".env", extra="ignore")


settings = Settings()
