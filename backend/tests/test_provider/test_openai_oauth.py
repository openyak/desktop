"""Tests for OpenAI OAuth PKCE token manager."""

from __future__ import annotations

import base64
import hashlib
import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.provider.openai_oauth import (
    extract_account_id,
    extract_email,
    generate_auth_url,
    is_token_expired,
)


def _make_jwt(payload: dict) -> str:
    """Create a fake JWT (header.payload.sig) for testing."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.sig"


class TestGenerateAuthUrl:
    def test_contains_pkce(self):
        url, verifier = generate_auth_url("http://localhost/cb", "state123")
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "state=state123" in url
        assert len(verifier) > 0

    def test_s256_challenge(self):
        url, verifier = generate_auth_url("http://localhost/cb", "s")
        # Extract code_challenge from URL
        import re
        match = re.search(r"code_challenge=([^&]+)", url)
        assert match
        challenge_from_url = match.group(1)
        # Verify it's SHA-256 of verifier
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        assert challenge_from_url == expected

    def test_verifier_uniqueness(self):
        _, v1 = generate_auth_url("http://x/cb", "s1")
        _, v2 = generate_auth_url("http://x/cb", "s2")
        assert v1 != v2


class TestExtractAccountId:
    def test_tier1_auth_claim(self):
        token = _make_jwt({
            "https://api.openai.com/auth": {"chatgpt_account_id": "acct_123"},
        })
        assert extract_account_id(token) == "acct_123"

    def test_tier2_organizations(self):
        token = _make_jwt({
            "https://api.openai.com/auth": {
                "organizations": [{"chatgpt_account_id": "acct_org"}],
            },
        })
        assert extract_account_id(token) == "acct_org"

    def test_tier3_org_id(self):
        token = _make_jwt({
            "https://api.openai.com/auth": {
                "organizations": [{"id": "org_456"}],
            },
        })
        assert extract_account_id(token) == "org_456"

    def test_tier4_top_level(self):
        token = _make_jwt({"chatgpt_account_id": "acct_top"})
        assert extract_account_id(token) == "acct_top"

    def test_no_account_raises(self):
        token = _make_jwt({"sub": "user123"})
        with pytest.raises(ValueError, match="No chatgpt_account_id"):
            extract_account_id(token)

    def test_invalid_jwt(self):
        with pytest.raises(ValueError, match="Invalid JWT"):
            extract_account_id("not-a-jwt")


class TestExtractEmail:
    def test_has_email(self):
        token = _make_jwt({"email": "user@example.com"})
        assert extract_email(token) == "user@example.com"

    def test_no_email(self):
        token = _make_jwt({"sub": "user"})
        assert extract_email(token) == ""

    def test_invalid_jwt(self):
        assert extract_email("bad") == ""


class TestIsTokenExpired:
    def test_expired(self):
        past = int((time.time() - 600) * 1000)
        assert is_token_expired(past) is True

    def test_not_expired(self):
        future = int((time.time() + 3600) * 1000)
        assert is_token_expired(future) is False

    def test_within_buffer(self):
        almost = int((time.time() + 200) * 1000)  # Within 300s buffer
        assert is_token_expired(almost, buffer_seconds=300) is True

    def test_outside_buffer(self):
        safe = int((time.time() + 400) * 1000)
        assert is_token_expired(safe, buffer_seconds=300) is False
