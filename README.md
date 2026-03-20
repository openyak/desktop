[中文](README.zh-CN.md)

# OpenYak

**Your local AI assistant — private, powerful, personal.**

OpenYak is a full-featured desktop AI assistant that brings Claude Code-like agentic capabilities to open-source models. It's a local-first, privacy-focused alternative to proprietary AI assistants, with multi-agent support, tool calling, reasoning, and a complete permission system.

<!-- ![OpenYak Screenshot](docs/screenshot.png) -->

## Features

- **Multi-Agent System** — 7 built-in agents (build, plan, explore, general, compaction, title, summary) with configurable system prompts and permissions
- **21+ Built-in Tools** — File read/write/edit, bash execution, glob/grep search, web fetch/search, subtask spawning, todo management, artifact storage, and more
- **Real-time Streaming** — Resumable SSE streams with reconnection support, heartbeats, and event replay
- **4-Layer Permission Engine** — Global → Agent → User → Session permission hierarchy with allow/deny/ask rules
- **Reasoning Support** — Extended thinking with collapsible reasoning blocks and token tracking
- **Context Management** — Two-stage context compression (trim + LLM summarization), doom loop detection, output truncation
- **Desktop Application** — Native Tauri 2 app with system integration, deep linking, and NSIS installer
- **Multi-Model Support** — Any model via OpenRouter, including reasoning models, with dynamic model listing
- **Responsive UI** — Desktop sidebar, tablet collapsible, mobile sheet drawer
- **Dark/Light Theme** — System-aware theming with CSS variable architecture
- **Full-Text Search** — SQLite FTS5 for searching sessions and message content
- **Plugin & Skill System** — Extensible with project-scoped plugins, bundled skills, and MCP integration

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Zustand, TanStack Query |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), SQLite WAL, OpenAI SDK |
| **Desktop** | Tauri 2 (Rust), NSIS installer |
| **LLM Provider** | OpenRouter (primary), OpenAI-compatible providers |

## Quick Start

### Prerequisites

- **Node.js** 18+
- **Python** 3.12+
- **npm** 9+
- An **OpenRouter API key** ([get one here](https://openrouter.ai/keys))

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/aspect-build/openyak.git
cd openyak

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Install backend dependencies
cd backend && pip install -e ".[dev]" && cd ..

# 4. Configure environment
cd backend && cp .env.example .env
# Edit .env — set OPENYAK_OPENROUTER_API_KEY
cd ..

# 5. Start both frontend and backend
npm run dev:all
```

Open http://localhost:3000 in your browser.

### Desktop Mode

```bash
# Requires Rust toolchain + Tauri CLI
npm run dev:desktop
```

## Project Structure

```
openyak/
├── frontend/           # Next.js 15 React frontend
├── backend/            # Python FastAPI backend
├── desktop-tauri/      # Tauri 2 desktop wrapper (Rust)
├── scripts/            # Build & sync scripts
└── package.json        # Root workspace (dev scripts)
```

See [frontend/README.md](frontend/README.md) and [backend/README.md](backend/README.md) for detailed documentation.

## Development Scripts

| Script | Description |
|--------|-------------|
| `npm run dev:frontend` | Start frontend dev server (port 3000) |
| `npm run dev:backend` | Start backend dev server (port 8000) |
| `npm run dev:all` | Start frontend + backend concurrently |
| `npm run dev:desktop` | Start frontend + backend + Tauri dev |
| `npm run build:frontend` | Production build (static export for desktop) |
| `npm run build:backend` | Bundle backend with PyInstaller |
| `npm run build:desktop` | Build Tauri desktop installer |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENYAK_OPENROUTER_API_KEY` | OpenRouter API key | (required) |
| `OPENYAK_DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./data/openyak.db` |
| `OPENYAK_HOST` | Backend listen address | `0.0.0.0` |
| `OPENYAK_PORT` | Backend listen port | `8000` |
| `OPENYAK_DEBUG` | Debug mode | `false` |
| `NEXT_PUBLIC_API_URL` | Frontend → Backend API URL | `http://localhost:8000` |

## Building for Production

### Web

```bash
# Build frontend
npm run build:frontend

# Build backend (standalone executable)
npm run build:backend
```

### Desktop (Windows)

```bash
# Build Tauri installer (.msi / .exe)
npm run build:desktop
```

## License

[AGPL-3.0](LICENSE)
