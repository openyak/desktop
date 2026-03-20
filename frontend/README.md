[中文](README.zh-CN.md)

# OpenYak Frontend

Next.js 15 frontend providing a professional-grade Chat UI for the OpenYak backend, inspired by LibreChat's UX architecture.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start dev server (requires backend running on localhost:8000)
npm run dev

# Or start both frontend and backend from the project root
cd .. && npm run dev:all
```

Open http://localhost:3000 in your browser.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router + Turbopack) | 15 |
| Runtime | React | 19 |
| Language | TypeScript | 5.7 |
| Styling | Tailwind CSS | 4 |
| Components | shadcn/ui (Radix + Tailwind) | — |
| Client State | Zustand | 5 |
| Server State | TanStack Query | 5 |
| Icons | Lucide React | — |
| Markdown | react-markdown + remark-gfm + rehype-highlight | — |
| Theme | next-themes (dark/light/system) | — |
| Notifications | Sonner | — |
| i18n | i18next + react-i18next | — |
| Desktop | @tauri-apps/api | 2 |

## Architecture

```
src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                #   Root layout (fonts, theme, provider nesting)
│   ├── page.tsx                  #   Redirect to /c/new
│   ├── globals.css               #   CSS variable color system + global styles
│   └── (main)/                   #   Route group: main app shell
│       ├── layout.tsx            #     Sidebar + main content area layout
│       ├── c/new/page.tsx        #     New conversation (Landing page)
│       ├── c/[sessionId]/page.tsx #    Active conversation
│       └── settings/page.tsx     #     Settings page
│
├── components/
│   ├── providers/                # Provider layer
│   │   ├── theme-provider.tsx    #   next-themes dark/light
│   │   ├── query-provider.tsx    #   TanStack Query
│   │   └── app-providers.tsx     #   Compose all providers
│   │
│   ├── layout/                   # Layout components
│   │   ├── sidebar.tsx           #   Desktop sidebar (fixed 260px)
│   │   ├── sidebar-header.tsx    #   Logo + new chat button
│   │   ├── sidebar-search.tsx    #   Session search
│   │   ├── session-list.tsx      #   Session list (with search filter)
│   │   ├── session-item.tsx      #   Single session (highlight, delete, timestamp)
│   │   ├── sidebar-footer.tsx    #   Model/Agent selectors + theme toggle + settings
│   │   └── mobile-nav.tsx        #   Mobile drawer navigation (Sheet)
│   │
│   ├── chat/                     # Chat interface
│   │   ├── chat-view.tsx         #   Conversation orchestrator (messages + input + interactive prompts)
│   │   ├── chat-header.tsx       #   Session title + model badge
│   │   ├── chat-form.tsx         #   Input box (auto-expand + Agent/Model tags)
│   │   ├── chat-textarea.tsx     #   Auto-resizing textarea
│   │   ├── chat-actions.tsx      #   Send/Stop buttons
│   │   ├── landing.tsx           #   New conversation landing (Hero + conversation starters)
│   │   └── chat-footer.tsx       #   Footer disclaimer
│   │
│   ├── messages/                 # Message rendering
│   │   ├── message-list.tsx      #   Message list (auto-scroll to bottom)
│   │   ├── message-item.tsx      #   Single message container (routes to user/assistant)
│   │   ├── message-avatar.tsx    #   User/assistant avatar
│   │   ├── message-content.tsx   #   Content dispatcher (routes by part.type)
│   │   ├── user-message.tsx      #   User message
│   │   └── assistant-message.tsx #   Assistant message + streaming message (typing indicator)
│   │
│   ├── parts/                    # Message part renderers
│   │   ├── text-part.tsx         #   Markdown rendering (code blocks with copy button)
│   │   ├── reasoning-part.tsx    #   Collapsible reasoning trace
│   │   ├── tool-part.tsx         #   Tool call visualization (icon, status, duration, expandable I/O)
│   │   ├── step-indicator.tsx    #   Step marker (token usage, cost)
│   │   ├── compaction-part.tsx   #   Context compression notification
│   │   └── subtask-part.tsx      #   Subtask link
│   │
│   ├── interactive/              # Blocking interactive prompts
│   │   ├── permission-dialog.tsx #   Permission request (inline Allow/Deny card)
│   │   └── question-prompt.tsx   #   Question prompt (option buttons + free text input)
│   │
│   ├── selectors/                # Selectors
│   │   ├── model-selector.tsx    #   Model dropdown
│   │   ├── agent-selector.tsx    #   Agent selector (build/plan/explore)
│   │   └── model-badge.tsx       #   Current model tag
│   │
│   └── ui/                       # shadcn/ui base components
│       └── button, dialog, sheet, scroll-area, select, tooltip,
│           skeleton, separator, badge, avatar, collapsible,
│           dropdown-menu, input, popover
│
├── hooks/                        # Custom hooks
│   ├── use-chat.ts               #   Core chat hook (prompt → stream → assemble)
│   ├── use-sse.ts                #   SSE connection + event dispatch to chatStore
│   ├── use-sessions.ts           #   TanStack Query: session CRUD
│   ├── use-messages.ts           #   TanStack Query: message fetching
│   ├── use-models.ts             #   TanStack Query: model list
│   ├── use-agents.ts             #   TanStack Query: agent list
│   ├── use-auto-resize.ts        #   Textarea auto-height
│   ├── use-scroll-anchor.ts      #   Auto-scroll to bottom
│   └── use-mobile.ts             #   Mobile breakpoint detection
│
├── stores/                       # Zustand state management
│   ├── chat-store.ts             #   Streaming generation state (real-time parts assembly)
│   ├── sidebar-store.ts          #   Sidebar visibility + search
│   └── settings-store.ts         #   User preferences (model, agent, persisted to localStorage)
│
├── lib/                          # Utilities
│   ├── api.ts                    #   Typed fetch wrapper (type-safe, error handling)
│   ├── sse.ts                    #   SSE client (reconnection, heartbeat timeout)
│   ├── utils.ts                  #   cn(), formatRelativeTime(), truncate()
│   └── constants.ts              #   API route constants, query key factory
│
├── types/                        # TypeScript types (mirrors backend schemas)
│   ├── session.ts                #   SessionResponse, SessionCreate
│   ├── message.ts                #   MessageResponse, PartData union type
│   ├── chat.ts                   #   PromptRequest, PromptResponse
│   ├── streaming.ts              #   SSE event types, PermissionRequest, QuestionRequest
│   ├── agent.ts                  #   AgentInfo, PermissionRule
│   └── model.ts                  #   ModelInfo, ModelCapabilities
│
└── i18n/                         # Internationalization
    └── locales/{lang}/{ns}.json  #   Translation files (en, zh)
```

## Layout Design

```
┌──────────────────────────────────────────────────────────┐
│                    Root Layout                           │
│  ThemeProvider → QueryProvider → Toaster → children      │
├───────────┬──────────────────────────────────────────────┤
│           │                                              │
│  Sidebar  │           Main Content                       │
│  260px    │                                              │
│  fixed    │  ┌──────────────────────────────────────┐    │
│           │  │ ChatHeader (title, model badge)      │    │
│ ┌───────┐ │  ├──────────────────────────────────────┤    │
│ │ Logo  │ │  │                                      │    │
│ │+ New  │ │  │ MessageList                          │    │
│ ├───────┤ │  │   ├── UserMessage                    │    │
│ │Search │ │  │   ├── AssistantMessage               │    │
│ ├───────┤ │  │   │   ├── TextPart (markdown)        │    │
│ │Session│ │  │   │   ├── ReasoningPart (collapsible) │   │
│ │List   │ │  │   │   ├── ToolPart (expandable)      │    │
│ │       │ │  │   │   └── StepIndicator              │    │
│ ├───────┤ │  │   └── StreamingMessage (typing)      │    │
│ │Model  │ │  ├──────────────────────────────────────┤    │
│ │Select │ │  │ PermissionDialog / QuestionPrompt    │    │
│ │Agent  │ │  ├──────────────────────────────────────┤    │
│ │Select │ │  │ ChatForm                             │    │
│ ├───────┤ │  │ ┌────────────────────────────┬─────┐ │    │
│ │Theme  │ │  │ │ Textarea (auto-resize)     │Send │ │    │
│ │Toggle │ │  │ └────────────────────────────┴─────┘ │    │
│ │       │ │  │ [agent badge] [model badge]          │    │
│ └───────┘ │  └──────────────────────────────────────┘    │
├───────────┴──────────────────────────────────────────────┤
│  MobileNav (≤768px, Sheet drawer)                        │
└──────────────────────────────────────────────────────────┘
```

## State Management

```
┌──────────────────────────────────────────┐
│          TanStack Query v5               │
│     Server state (cache + sync)          │
│  sessions, messages, models, agents      │
├──────────────────────────────────────────┤
│             Zustand                      │
│         Client state (reactive)          │
│  chatStore: streaming state, parts       │
│  sidebarStore: sidebar toggle, search    │
│  settingsStore: model, agent prefs       │
├──────────────────────────────────────────┤
│           next-themes                    │
│       Theme state (dark/light/system)    │
└──────────────────────────────────────────┘
```

## SSE Streaming Data Flow

```
User sends message
       │
       ▼
POST /api/chat/prompt { text, session_id?, model, agent }
       │
       ▼
Returns { stream_id, session_id }
       │
       ├─► chatStore.startGeneration()
       ▼
EventSource → /api/chat/stream/{stream_id}
       │
       ▼  SSE event dispatch
  ┌────────────────────────────────────────────────┐
  │ text_delta       → chatStore.appendTextDelta() │
  │ reasoning_delta  → chatStore.appendReasoning() │
  │ tool_start       → chatStore.addToolStart()    │
  │ tool_result      → chatStore.setToolResult()   │
  │ tool_error       → chatStore.setToolError()    │
  │ step_start/finish → chatStore.addStep*()       │
  │ permission_request → show PermissionDialog     │
  │ question          → show QuestionPrompt        │
  │ done → finishGeneration() + invalidate queries │
  │ error → toast.error() + finish                 │
  └────────────────────────────────────────────────┘
```

## Responsive Design

| Breakpoint | Behavior |
|------------|----------|
| `≥1024px` (lg) | Sidebar pinned, main area `ml-[260px]` |
| `768-1023px` (md) | Sidebar collapsible |
| `<768px` (sm) | Sidebar hidden, Sheet drawer mode |

## Theme System

CSS variable-based monochrome + Indigo color system, supporting dark/light/system modes:

- **Surface**: primary / secondary / tertiary / chat — four-level backgrounds
- **Text**: primary / secondary / tertiary — three-level text
- **Border**: default / heavy — two-level borders
- **Brand**: primary brand color
- **Semantic**: success / warning / destructive
- **Tool**: pending / running / completed / error status colors

## Key Components

### MessageContent (Content Dispatcher)

Routes message parts to their corresponding renderer by `PartData.type`:

| Part Type | Renderer | Description |
|-----------|----------|-------------|
| `text` | TextPart | Markdown rendering, code blocks with copy button + language label |
| `reasoning` | ReasoningPart | Collapsible reasoning trace, expanded while streaming, collapsed on completion |
| `tool` | ToolPartView | Tool call card showing icon, status, duration; expandable input/output |
| `step-start` | StepIndicator | Step start divider |
| `step-finish` | StepIndicator | Step completion, shows token usage and cost |
| `compaction` | CompactionPart | Context compression notification |
| `subtask` | SubtaskPart | Subtask link, click to navigate to child session |

### ToolPartView (Tool Call Visualization)

12 tool types with dedicated icons, 4 states (pending/running/completed/error) with distinct colors and animations:

| Tool | Icon |
|------|------|
| read / write | FileText |
| edit | Pencil |
| bash | Terminal |
| glob | FolderSearch |
| grep | Search |
| web_fetch / web_search | Globe |
| task | GitBranch |
| question | HelpCircle |
| todo | ListTodo |

### Interactive Prompts

- **PermissionDialog**: Inline card with Allow/Deny buttons, responds via `POST /api/chat/respond`
- **QuestionPrompt**: Inline card with option buttons + free text input

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API address | `http://localhost:8000` |

## Scripts

```bash
npm run dev       # Dev server (Turbopack, port 3000)
npm run build     # Production build
npm run start     # Production mode
npm run lint      # ESLint check
```
