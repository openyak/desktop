# OpenYak Desktop — Smoke Test Checklist

> Date: 2026-03-23
> Covers: 22 bug fixes (8 P0 + 9 P1 + 5 P2) + 6 WONTFIX closures
> Tester: _______________

## How to Run

```bash
npm run dev:all    # Start backend (8000) + frontend (3000)
```

Open http://localhost:3000 in browser. For desktop-specific tests, use `npm run dev:desktop`.

---

## P0 — Critical Fixes

### P0-01: Rapid double-click no longer sends duplicate messages
**What was fixed:** Added synchronous `useRef` guard in ChatForm to prevent double-click race condition.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Open any chat session | Chat loads normally | |
| 2 | Type "hello" in the input | Text appears | |
| 3 | Click Send button 5 times rapidly | Only 1 message appears in conversation | |
| 4 | Press Enter twice quickly | Only 1 message appears | |
| 5 | Wait for response to complete | Response renders correctly | |
| 6 | After response, type and send again | Works normally (guard resets) | |

---

### P0-02: Draft text preserved across session switches
**What was fixed:** Module-level draft cache saves input + attachments on unmount, restores on mount.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Open Session A, type "draft message" | Text in input box | |
| 2 | Attach a file (drag & drop or browse) | File chip appears | |
| 3 | Click Session B in sidebar | Session B loads | |
| 4 | Click Session A in sidebar | "draft message" + file attachment restored | |
| 5 | Send the message | Message sends, draft cleared | |
| 6 | Switch away and back to Session A | Input is empty (no stale draft) | |
| 7 | Restart the app, check Session A | Input is empty (drafts are ephemeral) | |

---

### P0-03: Generation aborts when switching sessions
**What was fixed:** ChatView cleanup calls `stopGeneration()` on session change during active generation.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Send a long prompt in Session A | Generation starts (spinner visible) | |
| 2 | Click Session B mid-generation | Session B loads cleanly | |
| 3 | Check Network tab | `POST /api/chat/abort` request visible | |
| 4 | Return to Session A | Partial response visible, no stuck spinner | |
| 5 | Send a new message in Session A | Works normally | |

---

### P0-04: No SSE stream pollution across sessions
**What was fixed:** Module-level SSE state reset when navigating away during generation.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Send prompt in Session A | Generation starts | |
| 2 | Switch to Session B mid-generation | Session B loads cleanly | |
| 3 | Send prompt in Session B | Session B response contains NO content from Session A | |
| 4 | Return to Session A | Shows partial response from before abort | |

---

### P0-05: Delete during generation doesn't stuck the UI
**What was fixed:** Frontend aborts before delete; backend publishes DONE on IntegrityError.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Send a long prompt in Session A | Generation starts | |
| 2 | Delete Session A from sidebar | Navigates to /c/new cleanly, no stuck spinner | |
| 3 | Check: no "generating" indicator | UI is idle | |
| 4 | Start generation in Session B, delete Session C (different) | Session B generation continues unaffected | |

---

### P0-06: Tool errors persisted to database
**What was fixed:** `except Exception` and `except RejectedError` blocks now call `update_part_data(status="error")`.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Ask the AI to do something that triggers a tool error (e.g., read a non-existent file path) | Tool shows as "error" in UI | |
| 2 | Refresh the page | Tool still shows as "error" (not stuck on "running") | |

---

### P0-07: Bad MCP connector doesn't block app startup
**What was fixed:** Per-connector try-except in MCP startup loop.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | (If you have MCP connectors configured) Start the app | App starts successfully | |
| 2 | Check backend logs | Any failed connectors logged as errors, not crashes | |
| 3 | Other features work normally | Chat, tools, etc. all functional | |

*Note: If no MCP connectors are configured, this test can be skipped.*

---

### P0-08: Skip onboarding redirects to provider setup
**What was fixed:** `handleSkip()` now calls `router.push("/models")` after `completeOnboarding()`.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Clear localStorage (or use incognito) | Fresh state | |
| 2 | App shows onboarding screen | Welcome screen visible | |
| 3 | Click "Skip, I'll use my own API key" | Redirected to /models page (not chat) | |
| 4 | Configure a provider (e.g., paste API key) | Provider activates | |
| 5 | Navigate to chat | Chat works, input is enabled | |

---

## P1 — Medium Priority Fixes

### P1-01: Permission timeout auto-denies
**What was fixed:** `useEffect` fires `onRespond(false)` when permission dialog expires.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Trigger a tool that requires permission (e.g., write a file with "ask" mode) | Permission dialog appears | |
| 2 | Wait for timeout (5 minutes, or shorten for testing) | Dialog auto-denies, shows "timed out" | |
| 3 | Agent continues execution (skipping the denied action) | No stuck state | |

*Note: 5-minute wait may be impractical. Verify by inspecting the `useEffect` code logic.*

---

### P1-02: Abort failure logged with warning
**What was fixed:** `console.warn` added in `stopGeneration` catch block.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start generation, then click Stop | Generation stops | |
| 2 | (Optional) Simulate network failure during abort | Console shows warning about backend possibly still generating | |

---

### P1-03: No blank flash after generation completes
**What was fixed:** Fallback now hides when new messages arrive, not on fixed 800ms timer.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Send a prompt and wait for response to complete | Response appears | |
| 2 | Watch carefully at the moment generation finishes | No blank flash between streaming and final message | |
| 3 | Repeat with a slow network (throttle to 3G) | Still no flash (fallback waits for DB message) | |

---

### P1-04: Send failure shows longer toast
**What was fixed:** Toast duration extended from 3s to 8s. Input restored via `result === false`.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Disconnect network / stop backend | Backend unreachable | |
| 2 | Type "test" and click Send | Error toast appears and stays ~8 seconds | |
| 3 | Input text is restored (not lost) | "test" reappears in input box | |

---

### P1-07: Model loading state distinguished from no-provider
**What was fixed:** Shows spinner + "Loading models..." when `isLoading && activeProvider`.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Open app with a provider configured | Header shows model name or loading spinner | |
| 2 | During initial model fetch | Spinner + "Loading models..." (not "Setup Provider") | |
| 3 | After models load | Model name appears | |
| 4 | With no provider configured | Shows "Setup Provider" button | |

---

### P1-08: DESYNC clears stale streaming content
**What was fixed:** `clearStreamingContent()` called on DESYNC before refetch.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | (Difficult to trigger manually) This fires when backend drops SSE events | Streaming content is cleared, DB messages refetched | |

*Note: Hard to test manually. Code review verification is sufficient.*

---

### P1-10: Busy server returns error instead of hanging
**What was fixed:** Semaphore acquire has 30-second timeout, returns "Server is busy" on timeout.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | (Difficult to trigger with 20 concurrent limit) | Under extreme load, new requests get "Server is busy" error | |

*Note: Hard to test manually. Code review verification is sufficient.*

---

### P1-12: Compaction failure notifies frontend
**What was fixed:** `compaction-error` SSE event published on failure.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | (Difficult to trigger manually) This fires when context compression fails | Frontend receives compaction-error event | |

*Note: Hard to test manually. Code review verification is sufficient.*

---

### P1-13: Session list retry uses exponential backoff
**What was fixed:** Replaced fixed 3s interval with exponential backoff (3s → 6s → 12s → 30s cap, 10 max).

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Stop the backend | Backend down | |
| 2 | Open the app / refresh | Sidebar shows loading | |
| 3 | Watch Network tab | Retry intervals increase (3s, 6s, 12s...) | |
| 4 | After 10 retries | Stops retrying | |
| 5 | Restart backend | Session list loads on next manual action | |

---

## P2 — Low Priority Fixes

### P2-01: OTP verification shows expiry countdown
**What was fixed:** 10-minute countdown timer shown during email verification.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start registration flow, enter email | Verification step appears | |
| 2 | Check below the email confirmation text | "Code expires in 9:59" countdown visible | |
| 3 | Countdown ticks every second | Timer decreases | |
| 4 | Click "Resend code" | Countdown resets to 10:00 | |

---

### P2-02: Ollama auto-detected after onboarding
**What was fixed:** Ollama status polls every 10s when no provider is set.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Start app with no provider configured | No provider active | |
| 2 | Start Ollama externally | Ollama running | |
| 3 | Wait ~10 seconds | Provider auto-detects to "ollama", models appear | |

---

### P2-03: Session rename updates instantly
**What was fixed:** Optimistic cache update with rollback on error.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Right-click a session → Rename | Edit mode appears | |
| 2 | Type new name, press Enter | Title updates instantly (no 1-2s lag) | |
| 3 | Refresh page | New title persists | |

---

### P2-06: Web search quota is thread-safe
**What was fixed:** `asyncio.Lock` protects global quota variables.

*Code review verification only — race condition is non-deterministic.*

---

### P2-07: Error messages don't leak internal details
**What was fixed:** AGENT_ERROR sends generic message; full error logged server-side only.

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Trigger a generation error (e.g., invalid model ID) | Error message shown in chat | |
| 2 | Check error text | Shows "An internal error occurred" (no file paths or stack traces) | |
| 3 | Check backend logs | Full error details logged there | |

---

## WONTFIX — Closed Issues (Not Bugs)

| ID | Reason |
|----|--------|
| P1-05 | Feature request: BYOK key health check is a new feature, not a bug |
| P1-06 | Feature request: ChatGPT subscription expiry detection is a new feature |
| P1-09 | `main.py` has global `loop.set_exception_handler()` that catches unhandled task exceptions |
| P1-11 | Empty LLM response returning `"continue"` is by design; 50-step cap provides protection |
| P2-04 | Ollama pull error actually persists in UI (not auto-dismissed); original issue description was incorrect |
| P2-05 | `finally` block already pops Future from `_response_futures` dict; no leak exists |

---

## Sign-off

| Area | Tester | Date | Result |
|------|--------|------|--------|
| P0 fixes | | | |
| P1 fixes | | | |
| P2 fixes | | | |
| Regression (existing features still work) | | | |
