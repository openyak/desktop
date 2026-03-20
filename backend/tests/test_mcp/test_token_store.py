"""Tests for app.mcp.token_store — OAuth token persistence."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

import json
from pathlib import Path

from app.mcp.oauth import AuthServerMeta, TokenSet
from app.mcp.token_store import McpTokenStore


def _make_tokens(**kwargs) -> TokenSet:
    defaults = {"access_token": "at_123", "refresh_token": "rt_456", "expires_at": 99999999.0}
    defaults.update(kwargs)
    return TokenSet(**defaults)


def _make_auth_meta() -> AuthServerMeta:
    return AuthServerMeta(
        authorization_endpoint="https://auth.example.com/authorize",
        token_endpoint="https://auth.example.com/token",
        scopes=["read"],
        resource_url="https://mcp.example.com/sse",
    )


class TestMcpTokenStore:
    def test_save_and_get_round_trip(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        tokens = _make_tokens()
        store.save("slack", tokens)
        got = store.get("slack")
        assert got is not None
        assert got.access_token == "at_123"
        assert got.refresh_token == "rt_456"
        assert got.expires_at == 99999999.0

    def test_get_nonexistent(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        assert store.get("nonexistent") is None

    def test_has_token(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        store.save("slack", _make_tokens())
        assert store.has_token("slack") is True
        assert store.has_token("other") is False

    def test_delete(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        store.save("slack", _make_tokens())
        store.delete("slack")
        assert store.has_token("slack") is False

    def test_save_with_auth_meta(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        store.save("slack", _make_tokens(), auth_meta=_make_auth_meta())
        meta = store.get_auth_meta("slack")
        assert meta is not None
        assert meta.authorization_endpoint == "https://auth.example.com/authorize"
        assert meta.scopes == ["read"]

    def test_get_auth_meta_none(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        store.save("slack", _make_tokens())  # no auth_meta
        assert store.get_auth_meta("slack") is None

    def test_client_id_round_trip(self, tmp_path: Path):
        store = McpTokenStore(project_dir=str(tmp_path))
        store.save_client_id("slack", "cid_123")
        assert store.get_client_id("slack") == "cid_123"

    def test_persistence_to_disk(self, tmp_path: Path):
        store1 = McpTokenStore(project_dir=str(tmp_path))
        store1.save("slack", _make_tokens())
        # New instance reads from disk
        store2 = McpTokenStore(project_dir=str(tmp_path))
        got = store2.get("slack")
        assert got is not None
        assert got.access_token == "at_123"


class TestMigrateNamespacedKeys:
    def test_migrates_colon_key(self, tmp_path: Path):
        # Pre-populate JSON with namespaced key
        tokens_path = tmp_path / ".openyak" / "mcp-tokens.json"
        tokens_path.parent.mkdir(parents=True)
        tokens_path.write_text(json.dumps({
            "engineering:slack": {"access_token": "at", "expires_at": 100}
        }))
        store = McpTokenStore(project_dir=str(tmp_path))
        assert store.get("slack") is not None
        assert store.has_token("engineering:slack") is False

    def test_keeps_latest_expiry(self, tmp_path: Path):
        tokens_path = tmp_path / ".openyak" / "mcp-tokens.json"
        tokens_path.parent.mkdir(parents=True)
        tokens_path.write_text(json.dumps({
            "a:slack": {"access_token": "old", "expires_at": 100},
            "b:slack": {"access_token": "new", "expires_at": 200},
        }))
        store = McpTokenStore(project_dir=str(tmp_path))
        got = store.get("slack")
        assert got is not None
        assert got.access_token == "new"

    def test_no_migration_needed(self, tmp_path: Path):
        tokens_path = tmp_path / ".openyak" / "mcp-tokens.json"
        tokens_path.parent.mkdir(parents=True)
        tokens_path.write_text(json.dumps({
            "slack": {"access_token": "at", "expires_at": 100}
        }))
        store = McpTokenStore(project_dir=str(tmp_path))
        assert store.get("slack") is not None
