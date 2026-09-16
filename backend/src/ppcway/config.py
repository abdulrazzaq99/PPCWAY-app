"""Settings, read once at start, refused by name when something is missing.

Blueprint 11.6: a service that boots with a missing credential and fails only when
the first merchant arrives is far more expensive to diagnose. Values come from the
environment, then `backend/.env`, then `web/.env` (where the owner keeps the
Google credentials). Locally the database is a SQLite file and there is no Redis;
Neon and Upstash are for the deployment and arrive as DATABASE_URL and REDIS_URL. Names, never values, appear in
errors: `hide_input_in_errors` keeps a rejected key out of the traceback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]
_REPO = _BACKEND.parent
# Later files win, so backend/.env overrides web/.env.
ENV_FILES = (_REPO / "web" / ".env", _BACKEND / ".env")


class ConfigError(RuntimeError):
    """Raised at start when configuration is incomplete. Says which name, never which value."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in ENV_FILES if p.exists()),
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["dev", "test", "production"] = "dev"

    #: Local default: one SQLite file under backend/data. The deployment sets
    #: DATABASE_URL to Neon. (The VERCEL_-prefixed names in web/.env are the
    #: deployment's and are deliberately not read here.)
    database_url: str = "sqlite:///./data/ppcway.db"
    #: Absent locally. Sessions and rate limits use it once the sign-in lands.
    redis_url: str | None = None

    # The website audit.
    pagespeed_api_key: SecretStr | None = None
    #: Where the audit's headless browser and crawler may spend, per site.
    audit_crawl_max_pages: int = 25
    audit_crawl_timeout_seconds: int = 60
    audit_render_timeout_seconds: int = 45
    #: Screenshots of audited home pages, one folder per run.
    audit_shots_dir: str = "./data/shots"

    # The one door to Google. Present only in the service that talks to Google Ads.
    google_ads_developer_token: SecretStr | None = None
    google_ads_login_customer_id: str | None = None
    google_ads_api_version: str = "v25"
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = "http://localhost:3000/api/oauth/google/callback"
    google_oauth_token_key: SecretStr | None = None

    #: Where the Next.js app lives, for links in emails and redirects.
    web_url: str = "http://localhost:3000"

    @field_validator("environment", mode="before")
    @classmethod
    def _lowercase(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @field_validator("database_url", mode="before")
    @classmethod
    def _spell_postgres_for_psycopg3(cls, value: object) -> object:
        """Neon hands out `postgresql://`; SQLAlchemy reads that as psycopg2, which is not installed."""
        if isinstance(value, str):
            for bare in ("postgresql://", "postgres://"):
                if value.startswith(bare):
                    return "postgresql+psycopg://" + value[len(bare) :]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = sorted({str(e["loc"][0]) for e in exc.errors() if e["type"] == "missing"})
        if missing:
            raise ConfigError(
                "refusing to start; missing required configuration: " + ", ".join(missing)
            ) from None
        raise ConfigError("refusing to start; invalid configuration: " + str(exc)) from None
