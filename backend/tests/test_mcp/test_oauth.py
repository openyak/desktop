"""Tests for app.mcp.oauth — PKCE, auth URL building, header parsing."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

import base64
import hashlib
import time
from urllib.parse import parse_qs, urlparse

from app.mcp.oauth import (
    AuthServerMeta,
    TokenSet,
    _extract_resource_metadata_url,
    build_authorization_url,
    generate_pkce_pair,
)


class TestGeneratePkcePair:
    def test_verifier_length(self):
        verifier, _ = generate_pkce_pair()
        assert len(verifier) <= 128

    def test_challenge_is_sha256_base64url(self):
        verifier, challenge = generate_pkce_pair()
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
        assert challenge == expected

    def test_uniqueness(self):
        pairs = [generate_pkce_pair() for _ in range(10)]
        verifiers = [v for v, _ in pairs]
        assert len(set(verifiers)) == 10


def _make_auth_meta(**kwargs) -> AuthServerMeta:
    defaults = {
        "authorization_endpoint": "https://auth.example.com/authorize",
        "token_endpoint": "https://auth.example.com/token",
    }
    defaults.update(kwargs)
    return AuthServerMeta(**defaults)


class TestBuildAuthorizationUrl:
    def test_required_params(self):
        url = build_authorization_url(
            _make_auth_meta(),
            redirect_uri="http://localhost:8080/callback",
            state="abc123",
            code_challenge="challenge_val",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["response_type"] == ["code"]
        assert params["state"] == ["abc123"]
        assert params["code_challenge"] == ["challenge_val"]
        assert params["code_challenge_method"] == ["S256"]

    def test_includes_scopes(self):
        url = build_authorization_url(
            _make_auth_meta(scopes=["read", "write"]),
            redirect_uri="http://localhost/cb",
            state="s",
            code_challenge="c",
        )
        params = parse_qs(urlparse(url).query)
        assert params["scope"] == ["read write"]

    def test_includes_resource_url(self):
        url = build_authorization_url(
            _make_auth_meta(resource_url="https://mcp.example.com/sse"),
            redirect_uri="http://localhost/cb",
            state="s",
            code_challenge="c",
        )
        params = parse_qs(urlparse(url).query)
        assert params["resource"] == ["https://mcp.example.com/sse"]

    def test_client_id_omitted_when_empty(self):
        url = build_authorization_url(
            _make_auth_meta(),
            redirect_uri="http://localhost/cb",
            state="s",
            code_challenge="c",
            client_id="",
        )
        params = parse_qs(urlparse(url).query)
        assert "client_id" not in params

    def test_extra_params_merged(self):
        url = build_authorization_url(
            _make_auth_meta(),
            redirect_uri="http://localhost/cb",
            state="s",
            code_challenge="c",
            extra_params={"prompt": "consent"},
        )
        params = parse_qs(urlparse(url).query)
        assert params["prompt"] == ["consent"]


class TestExtractResourceMetadataUrl:
    def test_from_header(self):
        header = 'Bearer resource_metadata="https://example.com/.well-known/oauth-protected-resource"'
        result = _extract_resource_metadata_url(header, "https://mcp.example.com/sse")
        assert result == "https://example.com/.well-known/oauth-protected-resource"

    def test_fallback_to_wellknown(self):
        result = _extract_resource_metadata_url("Bearer", "https://mcp.example.com/sse")
        assert result == "https://mcp.example.com/.well-known/oauth-protected-resource"

    def test_multiple_parts(self):
        header = 'Bearer realm="mcp", resource_metadata="https://meta.example.com/rm"'
        result = _extract_resource_metadata_url(header, "https://mcp.example.com/sse")
        assert result == "https://meta.example.com/rm"


class TestTokenSetExpired:
    def test_not_expired_when_zero(self):
        ts = TokenSet(access_token="tok", expires_at=0)
        assert ts.expired is False

    def test_expired_in_past(self):
        ts = TokenSet(access_token="tok", expires_at=time.time() - 100)
        assert ts.expired is True

    def test_expired_within_buffer(self):
        # 30s from now is within 60s buffer
        ts = TokenSet(access_token="tok", expires_at=time.time() + 30)
        assert ts.expired is True

    def test_not_expired_far_future(self):
        ts = TokenSet(access_token="tok", expires_at=time.time() + 3600)
        assert ts.expired is False
