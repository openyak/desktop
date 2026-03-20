"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.agent import AgentRegistry
from app.config import Settings
from app.models.base import Base
from app.provider.openrouter import OpenRouterProvider
from app.provider.registry import ProviderRegistry
from app.tool.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def settings() -> Settings:
    """Load settings from .env (includes the real API key)."""
    return Settings(_env_file=str(Path(__file__).parent.parent / ".env"))


@pytest.fixture(scope="session")
def api_key(settings: Settings) -> str:
    key = settings.openrouter_api_key
    if not key:
        pytest.skip("OPENYAK_OPENROUTER_API_KEY not set")
    return key


# ---------------------------------------------------------------------------
# Database (in-memory SQLite per test function)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as session:
        async with session.begin():
            yield session


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_registry() -> AgentRegistry:
    return AgentRegistry()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    from app.main import _register_builtin_tools
    tr = ToolRegistry()
    _register_builtin_tools(tr)
    return tr


@pytest_asyncio.fixture
async def provider_registry(api_key: str) -> ProviderRegistry:
    """Real ProviderRegistry with OpenRouter (needs API key)."""
    registry = ProviderRegistry()
    provider = OpenRouterProvider(api_key)
    registry.register(provider)
    await registry.refresh_models()
    return registry


# ---------------------------------------------------------------------------
# Temp directory for file tool tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temp directory for file-based tool tests."""
    return tmp_path


# ---------------------------------------------------------------------------
# FastAPI test client (for API endpoint tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app_client(db_engine, session_factory):
    """Async HTTP client wired to the FastAPI app with a test database."""
    import httpx
    from unittest.mock import AsyncMock, MagicMock
    from app.main import create_app
    from app.config import Settings
    from app.dependencies import set_session_factory

    settings = Settings(
        openrouter_api_key="test-key",
        database_url="sqlite+aiosqlite://",
    )
    app = create_app(settings)

    # Wire up test DB via dependency override
    from app.dependencies import get_db

    async def _override_get_db():
        async with session_factory() as session:
            async with session.begin():
                yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.session_factory = session_factory
    app.state.engine = db_engine

    # Mock external registries
    mock_pr = MagicMock()
    mock_pr.all_models.return_value = []
    mock_pr.refresh_models = AsyncMock(return_value={})
    mock_pr.resolve_model.return_value = None
    mock_pr.health = AsyncMock(return_value={})
    app.state.provider_registry = mock_pr

    app.state.agent_registry = MagicMock()
    app.state.tool_registry = MagicMock()
    app.state.skill_registry = MagicMock()
    app.state.connector_registry = None
    app.state.plugin_manager = None
    app.state.stream_manager = None
    app.state.settings = settings

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        client.app = app  # expose for tests that need to tweak app.state
        yield client
