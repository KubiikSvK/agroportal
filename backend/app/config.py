from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices
from typing import Optional

class Settings(BaseSettings):
    database_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"))
    postgres_db: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_DB"))
    postgres_user: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_USER"))
    postgres_password: Optional[str] = Field(default=None, validation_alias=AliasChoices("POSTGRES_PASSWORD"))
    postgres_host: str = Field(default="db", validation_alias=AliasChoices("POSTGRES_HOST"))
    postgres_port: str = Field(default="5432", validation_alias=AliasChoices("POSTGRES_PORT"))
    api_key: str = Field(default="", validation_alias=AliasChoices("AGRO_API_KEY", "API_KEY"))
    secret_key: str

    class Config:
        env_file = ".env"
        extra = "ignore"

    def model_post_init(self, __context):
        if not self.database_url and self.postgres_db and self.postgres_user and self.postgres_password:
            self.database_url = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

settings = Settings()
