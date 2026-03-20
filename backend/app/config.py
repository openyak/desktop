"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENYAK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Provider ---
    openrouter_api_key: str = ""

    # --- OpenYak Cloud Proxy (billing mode) ---
    proxy_url: str = ""  # e.g. "https://api.openyak.app" — when set, LLM calls go through proxy
    proxy_token: str = ""  # JWT from OpenYak account login
    proxy_refresh_token: str = ""  # Refresh token for auto-renewal

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/openyak.db"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # --- Project ---
    project_dir: str = "."

    # --- Billing ---
    markup_percent: float = 20.0  # Platform markup on provider cost (%) — applied in proxy mode

    # --- Web Search ---
    daily_search_limit: int = 20  # Max free web_search calls per day (Free/BYOK)

    # --- Compaction ---
    compaction_auto: bool = True
    compaction_reserved: int = 20_000

    # --- Agents (loaded from YAML) ---
    agents: dict[str, Any] | None = None

    # --- MCP (loaded from YAML) ---
    mcp: dict[str, Any] | None = None

    # --- OpenAI OAuth (ChatGPT Subscription) ---
    openai_oauth_access_token: str = ""
    openai_oauth_refresh_token: str = ""
    openai_oauth_account_id: str = ""
    openai_oauth_expires_at: int = 0  # milliseconds since epoch
    openai_oauth_email: str = ""

    # --- Google Workspace MCP Proxy ---
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- Brave Search ---
    brave_search_api_key: str = ""

    # --- Full-Text Search ---
    fts_enabled: bool = True  # built-in FTS5, enabled by default (zero external deps)
    fts_auto_index: bool = True  # auto-index workspace on first access

    # --- Remote Access ---
    remote_access_enabled: bool = False
    remote_token_path: str = "data/remote_token.json"
    remote_tunnel_mode: str = "cloudflare"  # "cloudflare" | "manual"
    remote_tunnel_url: str = ""  # Manual tunnel URL (when mode="manual")
    remote_permission_mode: str = "auto"  # "auto" | "ask" | "deny"


@lru_cache
def get_settings() -> Settings:
    return Settings()
