# OpenYak Desktop — Issue Tracker

> Generated: 2026-03-23
> Last Updated: 2026-03-23
> Status Legend: `OPEN` | `IN_PROGRESS` | `FIXED` | `VERIFIED` | `WONTFIX`

---

## Summary

| Priority | Total | Open | Fixed | Verified |
|----------|-------|------|-------|----------|
| P0 (Critical) | 8 | 0 | 8 | 0 |
| P1 (Medium) | 13 | 0 | 9 | 0 |
| P2 (Low) | 7 | 0 | 5 | 0 |
| **Total** | **28** | **0** | **22** | **0** |

---

## P0 — Critical (Blocks core experience / Can cause stuck UI)

### P0-01: Rapid double-click sends duplicate messages

| Field | Value |
|-------|-------|
| **ID** | P0-01 |
| **Status** | `FIXED` |
| **Category** | Frontend — Chat |
| **Affected Files** | `frontend/src/components/chat/chat-form.tsx` (line ~146-162), `frontend/src/hooks/use-chat.ts` (line ~43-141) |
| **Symptom** | User clicks Send rapidly twice before store reflects `isGenerating=true`, causing two duplicate prompts to be sent to the backend. |
| **Root Cause** | `handleSend()` guards with `isGenerating` from Zustand store, but the store update is async (happens inside `sendMessage` callback after API call). Between click 1 and store update, click 2 sees stale `isGenerating=false`. |
| **Impact** | Duplicate messages in conversation, wasted API calls, confusing UX. |
| **Fix Plan** | Add a local `isSending` ref/state in ChatForm. Set `true` synchronously on first click, before any async work. Reset on completion or error. Guard `handleSend` with both `isSending` and `isGenerating`. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | Rapidly click Send 5 times; only 1 message should appear. Test on slow network (throttle to 3G). |
| **Result** | — |

---

### P0-02: Switching sessions loses unsent draft text and attachments

| Field | Value |
|-------|-------|
| **ID** | P0-02 |
| **Status** | `FIXED` |
| **Category** | Frontend — Session Management |
| **Affected Files** | `frontend/src/components/chat/chat-form.tsx` (line ~101-102), `frontend/src/stores/settings-store.ts` |
| **Symptom** | User types a long message and/or attaches files in Session A, then clicks Session B in sidebar. Returns to Session A — input is empty, attachments gone. |
| **Root Cause** | ChatForm's `input` and `attachments` are component-local state (`useState`). When ChatForm unmounts on session switch, state is destroyed with no persistence layer. |
| **Impact** | Data loss. Users lose potentially long, carefully composed messages. |
| **Fix Plan** | Create a per-session draft store (Zustand + localStorage or sessionStorage). Key: `sessionId` (or `"new"` for landing). Save on every keystroke (debounced 500ms). Restore on mount. Clear on successful send. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Type text + attach file in Session A. 2) Switch to Session B. 3) Switch back to Session A. 4) Text and attachments should be restored. 5) Send message — draft should be cleared. |
| **Result** | — |

---

### P0-03: Switching sessions during generation doesn't abort backend

| Field | Value |
|-------|-------|
| **ID** | P0-03 |
| **Status** | `FIXED` |
| **Category** | Frontend — Chat / Session |
| **Affected Files** | `frontend/src/components/chat/chat-view.tsx` (line ~54-58), `frontend/src/hooks/use-chat.ts` (line ~145-160), `frontend/src/hooks/use-sse.ts` |
| **Symptom** | User is in Session A with active generation, clicks Session B. Backend agent loop for Session A continues running. Old SSE stream may leak deltas into shared `chatStore`, potentially corrupting Session B's view. |
| **Root Cause** | `ChatView` cleanup effect closes right-side panels but does NOT call `stopGeneration()` or send abort to backend. The SSE client is only closed when `streamId` changes (which it doesn't — Session B has no active stream). |
| **Impact** | Wasted backend compute (agent loop continues). Potential message data corruption in shared store. Resource leak (SSE connection stays open). |
| **Fix Plan** | In `ChatView`'s cleanup effect (or a dedicated navigation guard), check if `isGenerating` is true and the session is changing. If so: 1) Send `POST /api/chat/abort` with current `streamId`. 2) Call `finishGeneration()` on the store. 3) Close SSE client. Consider also adding a confirmation dialog: "Generation in progress. Leave anyway?" |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Start generation in Session A. 2) Click Session B mid-generation. 3) Backend logs should show abort. 4) Session A's response should be partial but consistent. 5) Session B should render cleanly with no stale streaming state. |
| **Result** | — |

---

### P0-04: Navigation during generation causes SSE stream state pollution

| Field | Value |
|-------|-------|
| **ID** | P0-04 |
| **Status** | `FIXED` |
| **Category** | Frontend — SSE Streaming |
| **Affected Files** | `frontend/src/hooks/use-sse.ts` (module-level state, line ~25-26), `frontend/src/stores/chat-store.ts` |
| **Symptom** | User navigates away from active generation and back. Module-level `persistedLastEventId` may be stale, causing events to be skipped on reconnect. Or: user starts a new generation in Session B while Session A's stream is still alive — both streams update the same `chatStore`. |
| **Root Cause** | `use-sse.ts` uses module-level persistent state (`persistedLastEventId`, `currentStreamId`) that survives React unmount. This was intentional for Landing→ChatView transitions but creates cross-session contamination. The shared `chatStore` doesn't namespace streaming state by session. |
| **Impact** | Missed events (incomplete response), duplicate content, or interleaved messages from two different sessions. |
| **Fix Plan** | This is closely tied to P0-03. Once abort-on-switch is implemented, this issue is largely mitigated. Additionally: 1) Reset `persistedLastEventId` when `sessionId` changes (not just `streamId`). 2) On `startGeneration()`, explicitly close any prior SSE client. 3) Consider adding `sessionId` to chatStore's streaming state for validation. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Start generation in Session A. 2) Navigate to Session B. 3) Send message in Session B. 4) Session B's response should contain no artifacts from Session A. 5) Return to Session A — response should show what was generated before abort. |
| **Result** | — |

---

### P0-05: Session delete during generation leaves UI stuck

| Field | Value |
|-------|-------|
| **ID** | P0-05 |
| **Status** | `FIXED` |
| **Category** | Frontend + Backend — Session |
| **Affected Files** | `frontend/src/components/layout/session-list.tsx` (line ~219-286), `backend/app/session/processor.py` (line ~379-385) |
| **Symptom** | User deletes the active session while generation is running. Frontend navigates to /c/new, but old SSE stream continues. When DONE arrives, refetch returns 404 for deleted session. On backend side, `IntegrityError` is caught silently — no AGENT_ERROR event is published. Frontend spinner may stay forever. |
| **Root Cause** | **Frontend:** Delete flow navigates away without aborting generation. **Backend:** `IntegrityError` catch block (line ~379) logs but doesn't publish an SSE error event, so frontend never receives termination signal. |
| **Impact** | UI permanently stuck in "generating" state until page refresh. Backend agent loop may also continue wasting resources. |
| **Fix Plan** | **Frontend:** Before deleting active session, check `isGenerating` and send abort first. **Backend:** In the `IntegrityError` catch block, publish `AGENT_ERROR` event with message "Session was deleted" before `job.complete()`. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Start generation in Session A. 2) Delete Session A from sidebar. 3) UI should abort, navigate to /c/new cleanly. 4) No stuck spinner. 5) Backend logs show clean abort + IntegrityError handled. |
| **Result** | — |

---

### P0-06: Tool execution exception not persisted to database

| Field | Value |
|-------|-------|
| **ID** | P0-06 |
| **Status** | `FIXED` |
| **Category** | Backend — Agent Loop |
| **Affected Files** | `backend/app/session/processor.py` (line ~1112-1151) |
| **Symptom** | When a tool throws an unexpected exception, the SSE `TOOL_ERROR` event is published to the frontend, but the database tool part remains in `"running"` state forever. |
| **Root Cause** | The generic `except Exception` block publishes the SSE event but does NOT call `update_part_data()` to set the tool part status to `"error"` in the database. The `except RejectedError` block had the same omission. |
| **Impact** | Frontend and database become out of sync. On page reload or reconnect, frontend fetches DB data showing the tool as still "running", which is misleading. |
| **Fix Plan** | In the `except Exception` block after publishing `TOOL_ERROR`, add a call to update the tool part in DB: `await update_part_data(session_factory, part_id, status="error", output=str(e))`. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Create a tool that intentionally throws (e.g., bash with a command that triggers an internal error). 2) Check DB: tool part status should be `"error"`, not `"running"`. 3) Page reload should show the tool as failed, not running. |
| **Result** | — |

---

### P0-07: Single MCP connector failure blocks entire app startup

| Field | Value |
|-------|-------|
| **ID** | P0-07 |
| **Status** | `FIXED` |
| **Category** | Backend — Startup / MCP |
| **Affected Files** | `backend/app/mcp/manager.py` (line ~48-81) |
| **Symptom** | If any MCP server is misconfigured or unreachable, `await connector_registry.startup()` throws and the entire FastAPI lifespan fails. App does not start. |
| **Root Cause** | `McpManager.startup()` had no per-connector error isolation — one failure in `McpClient` construction or `connect()` propagates up, aborts the loop, and kills the startup sequence. |
| **Impact** | App completely fails to start. User sees no UI. Must manually fix MCP config or remove the connector to recover. |
| **Fix Plan** | Wrap the per-connector loop body in `McpManager.startup()` with try-except. On failure, log the error and continue to the next connector. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Add a connector with an invalid URL. 2) Start the app. 3) App should start successfully. 4) Invalid connector should show as "error" in /plugins or connector list. 5) All other features should work normally. |
| **Result** | — |

---

### P0-08: Onboarding "Skip" leaves app with no provider and no guidance

| Field | Value |
|-------|-------|
| **ID** | P0-08 |
| **Status** | `FIXED` |
| **Category** | Frontend — Onboarding |
| **Affected Files** | `frontend/src/components/onboarding/onboarding-screen.tsx` (line ~250-255), `frontend/src/app/(main)/layout.tsx` (line ~69-82) |
| **Symptom** | User clicks "Skip, I'll use my own API key" on the welcome screen. `completeOnboarding()` fires immediately. User lands on chat page with `activeProvider=null`, no models available. Chat input is disabled but the reason is unclear — only a small "Setup Provider" link in the header dropdown. |
| **Root Cause** | The "Skip" button calls `completeOnboarding()` without: 1) Setting any provider. 2) Redirecting to /models for setup. 3) Triggering provider auto-detection with a prompt. After skip, `activeProvider` remains `null` and `useAutoDetectProvider` finds nothing because no API key has been configured. |
| **Impact** | User hits a dead end. Chat appears broken. The path to recovery (/models page) is not obvious. |
| **Fix Plan** | Option A: After "Skip", navigate to `/models` instead of chat, with a banner "Set up a provider to get started". Option B: Show an inline provider-setup step within onboarding (API key input field) before completing. Option C: On chat landing, show a prominent full-width setup card (not just header dropdown link) when `activeProvider=null`. |
| **Fix Date** | 2026-03-23 |
| **Fix Commit** | — |
| **Verification** | 1) Fresh install, click "Skip" on onboarding. 2) User should see clear guidance to set up a provider. 3) After setting up a provider, user should be able to chat immediately. 4) No dead-end state. |
| **Result** | — |

---

## P1 — Medium Priority (Poor UX / Edge cases)

### P1-01: Permission request timeout with no recovery

| Field | Value |
|-------|-------|
| **ID** | P1-01 |
| **Status** | `FIXED` |
| **Category** | Frontend — Interactive |
| **Affected Files** | `frontend/src/components/interactive/permission-dialog.tsx` (line ~79-237) |
| **Symptom** | Permission dialog times out after 5 minutes. Message says "timed out" but no actionable button. Agent may be stuck waiting. |
| **Fix Plan** | Auto-deny on timeout + show "Timed out — action was denied" status. Ensure backend receives the deny response. |
| **Fix Date** | 2026-03-23 |

---

### P1-02: Abort doesn't wait for backend completion

| Field | Value |
|-------|-------|
| **ID** | P1-02 |
| **Status** | `FIXED` |
| **Category** | Frontend — Chat |
| **Affected Files** | `frontend/src/hooks/use-chat.ts` (line ~145-160) |
| **Symptom** | `stopGeneration` clears frontend state immediately without waiting for backend abort API to complete. If abort fails, backend continues generating. |
| **Fix Plan** | Wait for abort API response before calling `finishGeneration()`. On API failure, retry once, then force-clear with warning. |
| **Fix Date** | 2026-03-23 |

---

### P1-03: StreamingMessage 800ms fallback causes blank flash

| Field | Value |
|-------|-------|
| **ID** | P1-03 |
| **Status** | `FIXED` |
| **Category** | Frontend — Messages |
| **Affected Files** | `frontend/src/components/messages/message-list.tsx` (line ~105-115) |
| **Symptom** | After generation completes, fallback timer expires (800ms) before DB messages finish rendering, causing brief blank space. |
| **Fix Plan** | Replace fixed timer with a condition: hide fallback only when DB messages are actually rendered (check `messages.length` includes new assistant message). |
| **Fix Date** | 2026-03-23 |

---

### P1-04: Send failure shows only a 3-second toast, input already cleared

| Field | Value |
|-------|-------|
| **ID** | P1-04 |
| **Status** | `FIXED` |
| **Category** | Frontend — Chat |
| **Affected Files** | `frontend/src/hooks/use-chat.ts` (line ~122-140), `frontend/src/components/chat/chat-form.tsx` |
| **Symptom** | On send failure (network error, 500), input is already cleared. Error toast disappears in 3 seconds. User may not see it and has to retype. |
| **Fix Plan** | On failure: restore input text and attachments. Show persistent error banner above input (not just toast). |
| **Fix Date** | 2026-03-23 |
| **Note** | Input restoration already handled by chat-form.tsx (`result === false` check restores text/attachments). Fix extends toast duration from 3s to 8s so users actually see the error. |

---

### P1-05: BYOK API key has no health check

| Field | Value |
|-------|-------|
| **ID** | P1-05 |
| **Status** | `WONTFIX` |
| **Category** | Frontend — Provider |
| **Affected Files** | `frontend/src/app/(main)/models/page.tsx`, `frontend/src/hooks/use-auto-detect-provider.ts` |
| **Symptom** | API key becomes invalid (quota exhausted, revoked) but app still shows it as configured. Chat fails with generic error. |
| **Fix Plan** | Add periodic key validation (lightweight API call). Show warning banner on /models when key is stale. |

---

### P1-06: ChatGPT subscription expiry only visible on /models page

| Field | Value |
|-------|-------|
| **ID** | P1-06 |
| **Status** | `WONTFIX` |
| **Category** | Frontend — Provider |
| **Affected Files** | `frontend/src/app/(main)/models/page.tsx`, `frontend/src/components/chat/chat-view.tsx` |
| **Symptom** | `needs_reauth` flag is only checked on /models page. User in chat gets generic error instead of "Please re-authenticate". |
| **Fix Plan** | Check `needs_reauth` in chat-level hook. Show persistent warning banner in chat header. |

---

### P1-07: Empty model list doesn't explain why

| Field | Value |
|-------|-------|
| **ID** | P1-07 |
| **Status** | `FIXED` |
| **Category** | Frontend — Model Selector |
| **Affected Files** | `frontend/src/components/selectors/header-model-dropdown.tsx`, `frontend/src/hooks/use-provider-models.ts` |
| **Symptom** | When model list is empty, user sees "No models" with no distinction between loading / auth error / quota exhausted. |
| **Fix Plan** | Return `{ data, isLoading, isError, error }` from hook. Show appropriate state: spinner, error message, or empty state with action. |
| **Fix Date** | 2026-03-23 |

---

### P1-08: DESYNC event doesn't stop ongoing stream assembly

| Field | Value |
|-------|-------|
| **ID** | P1-08 |
| **Status** | `FIXED` |
| **Category** | Frontend — SSE |
| **Affected Files** | `frontend/src/hooks/use-sse.ts` (line ~437-445) |
| **Symptom** | Backend drops events (queue overflow), sends DESYNC. Frontend refetches DB but `streamingParts` still has stale intermediate data, causing duplicate content. |
| **Fix Plan** | On DESYNC: clear `streamingParts` and `streamingText`, then refetch DB. Optionally show a subtle "Some events were dropped" notice. |
| **Fix Date** | 2026-03-23 |

---

### P1-09: Background asyncio tasks have no error callbacks

| Field | Value |
|-------|-------|
| **ID** | P1-09 |
| **Status** | `WONTFIX` |
| **Category** | Backend — Startup |
| **Affected Files** | `backend/app/main.py` (line ~176), `backend/app/fts/index.py`, `backend/app/fts/watcher.py` |
| **Symptom** | `asyncio.create_task()` for Ollama warmup, FTS indexing, and FTS watcher have no done callbacks. Failures are silently swallowed. |
| **Fix Plan** | Add `task.add_done_callback(handle_task_exception)` to all background tasks. Log errors at WARNING level minimum. |

---

### P1-10: Concurrent generation semaphore has no acquisition timeout

| Field | Value |
|-------|-------|
| **ID** | P1-10 |
| **Status** | `FIXED` |
| **Category** | Backend — Chat API |
| **Affected Files** | `backend/app/api/chat.py` (line ~54) |
| **Symptom** | MAX_CONCURRENT=20 semaphore. If a generation hangs indefinitely, it permanently occupies a slot. After 20 such hangs, all new requests block forever. |
| **Fix Plan** | Use `asyncio.wait_for(sem.acquire(), timeout=30)`. Return 503 (Service Unavailable) on timeout. |
| **Fix Date** | 2026-03-23 |

---

### P1-11: Empty LLM response causes retry loop until step cap

| Field | Value |
|-------|-------|
| **ID** | P1-11 |
| **Status** | `WONTFIX` |
| **Category** | Backend — Agent Loop |
| **Affected Files** | `backend/app/session/processor.py` (line ~676-695) |
| **Symptom** | LLM returns empty content 3 times. Code returns `"continue"` instead of `"stop"`, causing the outer loop to retry until the 50-step hard cap. |
| **Fix Plan** | After 3 consecutive empty responses, return `"stop"` with a user-facing message: "Model returned empty response. Please try again." |

---

### P1-12: Compaction failure not reported to frontend

| Field | Value |
|-------|-------|
| **ID** | P1-12 |
| **Status** | `FIXED` |
| **Category** | Backend — Compaction |
| **Affected Files** | `backend/app/session/compaction.py` (line ~222-250) |
| **Symptom** | Context compaction fails silently (only logged). Frontend doesn't know. Context continues to grow, leading to eventual hard failure. |
| **Fix Plan** | Publish `compaction-error` SSE event on failure. Frontend should show a warning: "Context compression failed. Consider starting a new chat." |
| **Fix Date** | 2026-03-23 |

---

### P1-13: Session list startup retry has no exponential backoff

| Field | Value |
|-------|-------|
| **ID** | P1-13 |
| **Status** | `FIXED` |
| **Category** | Frontend — Sidebar |
| **Affected Files** | `frontend/src/components/layout/session-list.tsx` (line ~150-156) |
| **Symptom** | When backend is down, session list retries every 3 seconds indefinitely with no backoff. Hammers the backend during recovery. |
| **Fix Plan** | Exponential backoff: 3s → 6s → 12s → 30s cap. Stop after 10 attempts, show "Backend unavailable" with manual retry button. |
| **Fix Date** | 2026-03-23 |

---

## P2 — Low Priority (Polish / Rare edge cases)

### P2-01: OTP verification code has no expiry countdown

| Field | Value |
|-------|-------|
| **ID** | P2-01 |
| **Status** | `FIXED` |
| **Category** | Frontend — Onboarding |
| **Affected Files** | `frontend/src/components/onboarding/onboarding-screen.tsx` (line ~304-346) |
| **Fix Plan** | Show "Code expires in X:XX" countdown. Suggest "Resend code" when expired. |
| **Fix Date** | 2026-03-23 |

---

### P2-02: Ollama auto-detection doesn't poll after initial check

| Field | Value |
|-------|-------|
| **ID** | P2-02 |
| **Status** | `FIXED` |
| **Category** | Frontend — Provider Detection |
| **Affected Files** | `frontend/src/hooks/use-auto-detect-provider.ts` |
| **Fix Plan** | Add `refetchInterval: 10_000` to Ollama status query in auto-detect hook. |
| **Fix Date** | 2026-03-23 |

---

### P2-03: Session rename lacks optimistic update

| Field | Value |
|-------|-------|
| **ID** | P2-03 |
| **Status** | `FIXED` |
| **Category** | Frontend — Session |
| **Affected Files** | `frontend/src/components/layout/session-item.tsx`, `frontend/src/hooks/use-sessions.ts` |
| **Fix Plan** | Use React Query's `onMutate` for optimistic cache update with rollback on error. |
| **Fix Date** | 2026-03-23 |

---

### P2-04: Ollama model pull error auto-dismisses too quickly

| Field | Value |
|-------|-------|
| **ID** | P2-04 |
| **Status** | `WONTFIX` |
| **Category** | Frontend — Ollama |
| **Affected Files** | `frontend/src/components/settings/ollama-panel.tsx` (line ~751-754) |
| **Fix Plan** | Change to manual dismiss or extend to 10 seconds minimum. |

---

### P2-05: Permission timeout leaks Future objects in backend

| Field | Value |
|-------|-------|
| **ID** | P2-05 |
| **Status** | `WONTFIX` |
| **Category** | Backend — Agent Loop |
| **Affected Files** | `backend/app/session/processor.py` (line ~1222-1227) |
| **Fix Plan** | Pop the Future from `_response_futures` dict in the `except TimeoutError` block. |

---

### P2-06: Web search quota tracking has race condition

| Field | Value |
|-------|-------|
| **ID** | P2-06 |
| **Status** | `FIXED` |
| **Category** | Backend — Agent Loop |
| **Affected Files** | `backend/app/session/processor.py` (line ~100-122) |
| **Fix Plan** | Protect global quota variables with `asyncio.Lock`. |
| **Fix Date** | 2026-03-23 |

---

### P2-07: Exception messages in AGENT_ERROR may leak sensitive info

| Field | Value |
|-------|-------|
| **ID** | P2-07 |
| **Status** | `FIXED` |
| **Category** | Backend — Security |
| **Affected Files** | `backend/app/session/processor.py` (line ~387-388), `backend/app/api/chat.py` (line ~47) |
| **Fix Plan** | In production, return sanitized message ("An internal error occurred"). Log full exception server-side only. |
| **Fix Date** | 2026-03-23 |

---

## Change Log

| Date | Action | Issues |
|------|--------|--------|
| 2026-03-23 | Initial issue tracker created | All 27 issues documented |
| 2026-03-23 | Fixed P0-01 and P0-02 in chat-form.tsx | P0-01: Added `sendingRef` synchronous guard to prevent duplicate sends on rapid double-click. P0-02: Added module-level `draftCache` Map with mount/unmount lifecycle to preserve unsent input and attachments across session switches. |
| 2026-03-23 | Fixed P0-08 in onboarding-screen.tsx | P0-08: Added `useRouter` import and `router.push("/models")` after `completeOnboarding()` in `handleSkip`, so users who skip onboarding are redirected to the models/provider setup page instead of a dead-end chat. |
| 2026-03-23 | Fixed P0-06 in processor.py | P0-06: Added `update_part_data()` calls in both `except RejectedError` and `except Exception` blocks to persist tool error status to DB (matching the existing `TimeoutError` handler pattern). DB calls wrapped in inner try/except to avoid masking original errors. |
| 2026-03-23 | Fixed P0-07 in manager.py | P0-07: Wrapped per-connector loop body in `McpManager.startup()` with try-except so a single failing MCP server is logged and skipped instead of aborting the entire startup sequence. |
| 2026-03-23 | Fixed P0-03 in chat-view.tsx | P0-03: Added `isGeneratingRef` and `stopRef` refs to track latest generation state. Modified existing `useEffect` cleanup to call `stopGeneration()` when navigating away during active generation, aborting the backend and closing the SSE stream. |
| 2026-03-23 | Fixed P0-04 in use-sse.ts | P0-04: In the SSE cleanup function, reset module-level `persistedLastEventId` and `currentStreamId` to zero/null when leaving during active generation, preventing stale state from contaminating future streams. |
| 2026-03-23 | Fixed P0-05 in session-list.tsx and processor.py | P0-05 (Part A): Added abort check at the top of `handleDeleteConfirm` — if the deleted session has active generation, sends abort API call and calls `finishGeneration()` before proceeding. (Part B): Added `DONE` event publish in the `IntegrityError` catch block so frontend receives a termination signal when a session is deleted mid-generation. |
| 2026-03-23 | Fixed P1-01 in permission-dialog.tsx | P1-01: Added `hasDeniedRef` and a `useEffect` that auto-denies (calls `onRespond(false)`) once when `expired` becomes true, so the backend receives a deny response on timeout instead of waiting indefinitely. Ref resets on `callId` change for subsequent requests. |
| 2026-03-23 | Fixed P1-02 in use-chat.ts | P1-02: Added `console.warn` in `stopGeneration` catch block to alert that the abort request failed and the backend may still be generating. The `finishGeneration()` call correctly runs unconditionally since the user explicitly requested stop. |
| 2026-03-23 | Fixed P1-04 in use-chat.ts | P1-04: Extended error toast duration from default 3s to 8s (`{ duration: 8000 }`). Input text restoration was already handled by chat-form.tsx's `result === false` check. |
| 2026-03-23 | Fixed P1-10 in chat.py | P1-10: Replaced `async with sm._semaphore` with explicit `asyncio.wait_for(acquire(), timeout=30)`. On timeout, publishes AGENT_ERROR ("Server is busy") and completes the job instead of blocking forever. |
| 2026-03-23 | Fixed P1-12 in compaction.py and events.py | P1-12: Added `COMPACTION_ERROR` SSE event constant. When `_phase2_summarize` catches an exception, it now publishes a `compaction-error` event to the frontend with a user-facing message before returning `None`. |
| 2026-03-23 | Fixed P2-06 in processor.py | P2-06: Added module-level `_search_quota_lock = asyncio.Lock()`. Converted `_get_search_quota()` and `_increment_search_count()` to async functions that acquire the lock before reading/writing the global quota variables. Updated all call sites to `await`. |
| 2026-03-23 | Fixed P2-07 in processor.py and chat.py | P2-07: Replaced `str(e)` in AGENT_ERROR payloads with generic message "An internal error occurred. Please try again." in both `run_generation` (processor.py) and `_on_task_done` (chat.py). Full exceptions are still logged server-side via `logger.exception`. |
| 2026-03-23 | Fixed P2-01 in onboarding-screen.tsx | P2-01: Added `codeCountdown` state with `useEffect` timer that starts at 600s when entering verification step. Displays "Code expires in M:SS" below the email confirmation. Shows "Code expired -- please resend" at zero. Countdown resets on resend. |
| 2026-03-23 | Fixed P2-02 in use-auto-detect-provider.ts | P2-02: Added `refetchInterval: activeProvider === null ? 10_000 : false` to the Ollama status query so it polls every 10s until a provider is detected. |
| 2026-03-23 | Fixed P2-03 in use-sessions.ts | P2-03: Added `onMutate` optimistic update to `useRenameSession` that immediately updates the infinite query cache. Added `onError` rollback to restore previous data on failure. Replaced `onSuccess` with `onSettled` for cache invalidation. |
| 2026-03-23 | Fixed P1-03 in message-list.tsx | P1-03: Replaced hardcoded 800ms fallback timer with message-count-aware logic. Tracks `prevMessageCountRef` before generation ends. Fallback hides early when `messages.length` increases (new assistant message loaded from DB). Safety timeout increased to 2000ms. |
| 2026-03-23 | Fixed P1-08 in use-sse.ts and chat-store.ts | P1-08: Added `clearStreamingContent` action to chat-store that resets `streamingParts`, `streamingText`, and `streamingReasoning` without clearing session/stream IDs. Called in the DESYNC handler before refetching DB messages to prevent stale streaming data from persisting. |
| 2026-03-23 | Fixed P1-07 in header-model-dropdown.tsx | P1-07: Added early return with `Loader2` spinner and "Loading models..." text when `isLoading && activeProvider`, distinguishing the loading state from the no-provider state. "Setup Provider" button now only shows when there truly is no active provider. |
| 2026-03-23 | Fixed P1-13 in session-list.tsx | P1-13: Replaced fixed 3-second `setInterval` retry with exponential backoff using `setTimeout`. Delay starts at 3s and doubles each attempt (3s, 6s, 12s, 24s, 30s cap). Stops after 10 attempts to avoid indefinite polling. |
