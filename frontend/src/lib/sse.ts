/**
 * SSE client with reconnection support.
 *
 * Uses native EventSource. Supports:
 * - Reconnection with last_event_id for replay
 * - Heartbeat timeout detection
 * - Exponential backoff with jitter
 * - Max retry limit with disconnection callback
 * - Per-event-type listeners
 */

import {
  SSE_HEARTBEAT_TIMEOUT,
  SSE_RECONNECT_DELAY,
  SSE_RECONNECT_MAX_DELAY,
  SSE_RECONNECT_BACKOFF,
  SSE_MAX_RETRIES,
} from "./constants";
import { getRemoteToken } from "./remote-connection";
import type { SSEEventData } from "@/types/streaming";

export type SSEEventHandler = (data: SSEEventData, id: number) => void;

export type SSEConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface SSEClientOptions {
  url: string;
  /**
   * Optional dynamic URL provider. Called before each (re)connect to resolve
   * the current URL. Use this when the backend may restart on a different port
   * (e.g., desktop mode). Falls back to `url` if not provided.
   */
  urlProvider?: () => string;
  /** Resume from a specific event ID (e.g., after component remount during navigation). */
  initialLastEventId?: number;
  /** Called when connection opens */
  onOpen?: () => void;
  /** Called on any error (before reconnect) */
  onError?: (error: Event) => void;
  /** Called when stream finishes (done event or permanent close) */
  onClose?: () => void;
  /** Called when connection status changes */
  onStatusChange?: (status: SSEConnectionStatus) => void;
  /** Called on any received event (for idle timeout tracking). */
  onEvent?: () => void;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private handlers = new Map<string, SSEEventHandler[]>();
  private lastEventId = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private staleCheckInterval: ReturnType<typeof setInterval> | null = null;
  private lastEventTime = 0;
  private closed = false;
  private paused = false;
  private retryCount = 0;
  // Track consecutive native auto-reconnect attempts without receiving an event.
  // If too many fire without success, we take over with custom reconnect logic.
  private nativeReconnectCount = 0;
  private static MAX_NATIVE_RECONNECTS = 2;

  constructor(private options: SSEClientOptions) {
    this.lastEventId = options.initialLastEventId ?? 0;
  }

  /** Update the base URL (e.g., after backend restarts on a new port). */
  updateUrl(newUrl: string): void {
    this.options.url = newUrl;
  }

  /** Register a handler for a specific event type. */
  on(eventType: string, handler: SSEEventHandler): this {
    const list = this.handlers.get(eventType) ?? [];
    list.push(handler);
    this.handlers.set(eventType, list);
    return this;
  }

  /** Start connecting. */
  connect(): void {
    this.closed = false;
    this.retryCount = 0;
    this.lastEventTime = Date.now();
    this.options.onStatusChange?.("connecting");
    this.doConnect();
    this.startStaleCheck();
  }

  /** Close the connection permanently. */
  close(): void {
    this.closed = true;
    this.clearTimers();
    if (this.staleCheckInterval) {
      clearInterval(this.staleCheckInterval);
      this.staleCheckInterval = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /** Check if the connection is still alive. If dead, trigger reconnect.
   *  Used after desktop wake/visibility restoration. */
  checkHealth(): void {
    if (this.closed) return;
    if (
      !this.eventSource ||
      this.eventSource.readyState === EventSource.CLOSED
    ) {
      // Connection is dead — force reconnect
      this.doConnect();
    } else {
      // Connection may look open but be stale. Reset heartbeat timer
      // so that if no event arrives soon, we'll reconnect.
      this.resetHeartbeat();
    }
  }

  /** Pause reconnection attempts (e.g., backend is restarting). */
  pauseReconnect(): void {
    this.paused = true;
    this.clearTimers();
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /** Resume and immediately attempt to reconnect. */
  resumeReconnect(): void {
    if (!this.paused) return;
    this.paused = false;
    this.retryCount = 0;
    this.doConnect();
  }

  private doConnect(): void {
    if (this.closed || this.paused) return;

    // Close any existing connection before creating a new one
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    // Resolve URL dynamically — picks up new backend port after restart
    const baseUrl = this.options.urlProvider?.() ?? this.options.url;
    // Build query params: last_event_id for reconnection, token for remote auth
    const params = new URLSearchParams();
    if (this.lastEventId > 0) params.set("last_event_id", String(this.lastEventId));
    const remoteToken = getRemoteToken();
    if (remoteToken) params.set("token", remoteToken);
    const qs = params.toString();
    const url = qs ? `${baseUrl}?${qs}` : baseUrl;

    const es = new EventSource(url);

    // Register all event listeners BEFORE the connection opens
    // to avoid missing any early events
    for (const eventType of this.handlers.keys()) {
      es.addEventListener(eventType, (e: Event) => {
        // `error` is special in EventSource: transport failures also dispatch a
        // native error Event (without `.data`). Ignore those here; they are
        // handled by `es.onerror` below.
        if (!(e instanceof MessageEvent)) {
          return;
        }

        this.nativeReconnectCount = 0;
        this.lastEventTime = Date.now();
        this.resetHeartbeat();
        this.options.onEvent?.();

        // Track event ID for reconnection
        if (e.lastEventId) {
          this.lastEventId = parseInt(e.lastEventId, 10);
        }

        let data: SSEEventData;
        try {
          data = JSON.parse(e.data) as SSEEventData;
        } catch {
          data = {} as SSEEventData;
        }

        const handlers = this.handlers.get(eventType) ?? [];
        for (const handler of handlers) {
          handler(data, this.lastEventId);
        }
      });
    }

    es.onopen = () => {
      this.retryCount = 0; // Reset on successful connection
      this.nativeReconnectCount = 0;
      this.lastEventTime = Date.now();
      this.resetHeartbeat();
      this.options.onStatusChange?.("connected");
      this.options.onOpen?.();
    };

    es.onerror = (e) => {
      this.options.onError?.(e);
      if (this.closed) return;

      if (es.readyState === EventSource.CLOSED) {
        // Permanently closed — use custom reconnect
        this.scheduleReconnect();
      } else if (es.readyState === EventSource.CONNECTING) {
        // Native auto-reconnect in progress. Track consecutive attempts
        // so we can detect silent failures (e.g., server cleaned up the job).
        this.nativeReconnectCount++;
        if (this.nativeReconnectCount > SSEClient.MAX_NATIVE_RECONNECTS) {
          // Too many native reconnects without receiving an event.
          // Take over with custom reconnect logic (has retry limits
          // and will eventually fire the "disconnected" callback).
          es.close();
          this.scheduleReconnect();
        }
      }
    };

    this.eventSource = es;
  }

  private resetHeartbeat(): void {
    if (this.heartbeatTimer) clearTimeout(this.heartbeatTimer);
    this.heartbeatTimer = setTimeout(() => {
      // No heartbeat received — server may be dead
      if (this.eventSource && !this.closed) {
        this.eventSource.close();
        this.scheduleReconnect();
      }
    }, SSE_HEARTBEAT_TIMEOUT);
  }

  private scheduleReconnect(): void {
    this.clearTimers();
    if (this.closed || this.paused) return;

    this.retryCount++;

    if (this.retryCount > SSE_MAX_RETRIES) {
      // Give up — notify the app that we're disconnected
      this.options.onStatusChange?.("disconnected");
      return;
    }

    this.options.onStatusChange?.("reconnecting");

    // Exponential backoff with jitter: delay * backoff^(retry-1) + random jitter
    const baseDelay = Math.min(
      SSE_RECONNECT_DELAY * Math.pow(SSE_RECONNECT_BACKOFF, this.retryCount - 1),
      SSE_RECONNECT_MAX_DELAY,
    );
    const jitter = baseDelay * 0.2 * (Math.random() - 0.5); // ±10%
    const delay = Math.round(baseDelay + jitter);

    this.reconnectTimer = setTimeout(() => {
      this.doConnect();
    }, delay);
  }

  /**
   * Proactive stale connection detection.
   *
   * Runs every 15s and checks if the last event was received longer ago than
   * the heartbeat timeout. This catches cases where the OS froze the network
   * stack (e.g., laptop sleep) and the heartbeat setTimeout never fired because
   * the JS event loop was also frozen.
   */
  private startStaleCheck(): void {
    if (this.staleCheckInterval) clearInterval(this.staleCheckInterval);
    this.staleCheckInterval = setInterval(() => {
      if (this.closed || !this.eventSource) return;
      const staleMs = Date.now() - this.lastEventTime;
      if (staleMs > SSE_HEARTBEAT_TIMEOUT) {
        // Connection is stale — force reconnect
        this.eventSource.close();
        this.eventSource = null;
        this.scheduleReconnect();
      }
    }, 15_000);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}
