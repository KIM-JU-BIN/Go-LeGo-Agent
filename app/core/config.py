"""환경변수와 애플리케이션 설정을 한 곳에서 관리합니다."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """실행 환경에 필요한 설정을 타입 안전하게 보관합니다.

    실제 Go-LeGo 프로젝트에 붙일 때도 환경변수 이름을 유지하면
    애플리케이션 코드가 환경에 직접 의존하지 않도록 할 수 있습니다.
    """

    app_name: str = Field(default="go-lego-agent", validation_alias="APP_NAME")
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    database_enabled: bool = Field(default=True, validation_alias="DATABASE_ENABLED")
    db_host: str = Field(default="127.0.0.1", validation_alias="MAPSERVICE_DB_HOST")
    db_port: int = Field(default=3306, validation_alias="MAPSERVICE_DB_PORT")
    db_user: str = Field(default="root", validation_alias="MAPSERVICE_DB_USER")
    db_password: str = Field(default="", validation_alias="MAPSERVICE_DB_PASSWORD")
    db_name: str = Field(default="barrier_free_db", validation_alias="MAPSERVICE_DB_NAME")
    db_pool_min_size: int = Field(default=1, validation_alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=5, validation_alias="DB_POOL_MAX_SIZE")

    max_agent_message_length: int = Field(default=200, validation_alias="MAX_AGENT_MESSAGE_LENGTH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """애플리케이션 전체에서 공유할 설정 객체를 한 번만 생성합니다."""
    return Settings()
