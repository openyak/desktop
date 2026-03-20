[English](README.md)

# OpenYak

**你的本地 AI 助手 — 私密、强大、个性化。**

OpenYak 是一个全功能桌面 AI 助手，为开源模型带来 Claude Code 级别的 agentic 能力。本地优先、隐私至上，支持多 agent 协作、工具调用、推理链和完整的权限管理系统。

<!-- ![OpenYak 截图](docs/screenshot.png) -->

## 功能特性

- **多 Agent 系统** — 7 个内置 agent（build、plan、explore、general、compaction、title、summary），可配置系统提示词和权限规则
- **21+ 内置工具** — 文件读写编辑、bash 执行、glob/grep 搜索、网页抓取/搜索、子任务派发、待办管理、Artifact 存储等
- **实时流式传输** — 可恢复的 SSE 流，支持断线重连、心跳检测和事件回放
- **4 层权限引擎** — 全局 → Agent → 用户 → 会话，支持 allow/deny/ask 三种规则
- **推理能力** — 扩展思维链，可折叠推理块，token 用量追踪
- **上下文管理** — 两阶段上下文压缩（裁剪 + LLM 摘要）、doom loop 检测、输出截断
- **桌面应用** — 原生 Tauri 2 应用，系统集成、深度链接、NSIS 安装包
- **多模型支持** — 通过 OpenRouter 接入任意模型（含推理模型），动态模型列表
- **响应式 UI** — 桌面端固定侧边栏、平板可折叠、移动端抽屉模式
- **暗色/亮色主题** — 跟随系统的主题切换，基于 CSS 变量体系
- **全文搜索** — SQLite FTS5 搜索会话和消息内容
- **插件与技能系统** — 支持项目级插件、内置技能和 MCP 集成

## 技术栈

| 层 | 技术 |
|----|------|
| **前端** | Next.js 15, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Zustand, TanStack Query |
| **后端** | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), SQLite WAL, OpenAI SDK |
| **桌面端** | Tauri 2 (Rust), NSIS 安装包 |
| **LLM 提供者** | OpenRouter（主要）, OpenAI 兼容接口 |

## 快速开始

### 前置要求

- **Node.js** 18+
- **Python** 3.12+
- **npm** 9+
- **OpenRouter API 密钥**（[获取地址](https://openrouter.ai/keys)）

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/aspect-build/openyak.git
cd openyak

# 2. 安装前端依赖
cd frontend && npm install && cd ..

# 3. 安装后端依赖
cd backend && pip install -e ".[dev]" && cd ..

# 4. 配置环境变量
cd backend && cp .env.example .env
# 编辑 .env，填入 OPENYAK_OPENROUTER_API_KEY
cd ..

# 5. 一键启动前后端
npm run dev:all
```

浏览器打开 http://localhost:3000 即可使用。

### 桌面模式

```bash
# 需要 Rust 工具链 + Tauri CLI
npm run dev:desktop
```

## 项目结构

```
openyak/
├── frontend/           # Next.js 15 React 前端
├── backend/            # Python FastAPI 后端
├── desktop-tauri/      # Tauri 2 桌面端封装（Rust）
├── scripts/            # 构建与同步脚本
└── package.json        # 根工作区（开发脚本）
```

详细文档请参阅 [frontend/README.zh-CN.md](frontend/README.zh-CN.md) 和 [backend/README.zh-CN.md](backend/README.zh-CN.md)。

## 开发脚本

| 脚本 | 说明 |
|------|------|
| `npm run dev:frontend` | 启动前端开发服务器（端口 3000） |
| `npm run dev:backend` | 启动后端开发服务器（端口 8000） |
| `npm run dev:all` | 同时启动前后端 |
| `npm run dev:desktop` | 同时启动前后端 + Tauri 开发模式 |
| `npm run build:frontend` | 生产构建（桌面端静态导出） |
| `npm run build:backend` | 使用 PyInstaller 打包后端 |
| `npm run build:desktop` | 构建 Tauri 桌面安装包 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENYAK_OPENROUTER_API_KEY` | OpenRouter API 密钥 | （必填） |
| `OPENYAK_DATABASE_URL` | 数据库连接字符串 | `sqlite+aiosqlite:///./data/openyak.db` |
| `OPENYAK_HOST` | 后端监听地址 | `0.0.0.0` |
| `OPENYAK_PORT` | 后端监听端口 | `8000` |
| `OPENYAK_DEBUG` | 调试模式 | `false` |
| `NEXT_PUBLIC_API_URL` | 前端连接后端地址 | `http://localhost:8000` |

## 生产构建

### Web 部署

```bash
# 构建前端
npm run build:frontend

# 打包后端（独立可执行文件）
npm run build:backend
```

### 桌面端（Windows）

```bash
# 构建 Tauri 安装包（.msi / .exe）
npm run build:desktop
```

## 许可证

[AGPL-3.0](LICENSE)
