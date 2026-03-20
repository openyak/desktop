import { api } from "./api";
import { API, IS_DESKTOP, resolveApiUrl, getBackendUrl } from "./constants";
import type { FileAttachment } from "@/types/chat";

export interface FileSearchResult {
  name: string;
  relative_path: string;
  absolute_path: string;
}

/**
 * Upload a single file to the backend (for drag-drop where path is unavailable).
 * Returns the FileAttachment metadata on success.
 * Includes SHA-256 dedup on the backend — identical content reuses existing file.
 *
 * Uses raw fetch (not api.post) because multipart/form-data
 * requires the browser to set Content-Type with boundary automatically.
 */
export async function uploadFile(file: File): Promise<FileAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(resolveApiUrl(API.FILES.UPLOAD), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Open a native OS file dialog via the backend and return selected files.
 * Files are referenced in-place — no copying to data/uploads.
 */
export async function browseFiles(): Promise<FileAttachment[]> {
  if (IS_DESKTOP) {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: true,
        directory: false,
        title: "Select files",
      });

      const paths = Array.isArray(selected)
        ? selected
        : selected
          ? [selected]
          : [];

      if (paths.length === 0) return [];
      return attachByPath(paths);
    } catch {
      // Fallback to backend-based picker for compatibility.
    }
  }

  // Use raw fetch — same reason as browseDirectory: avoid retry-on-timeout
  // opening duplicate OS dialogs.
  const url = IS_DESKTOP
    ? `${await getBackendUrl()}${API.FILES.BROWSE}`
    : resolveApiUrl(API.FILES.BROWSE);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ multiple: true, title: "Select files" }),
    signal: AbortSignal.timeout(600_000),
  });
  if (!res.ok) throw new Error(`Browse failed: ${res.status}`);
  return res.json() as Promise<FileAttachment[]>;
}

/**
 * Open a native OS directory picker and return selected path.
 */
export async function browseDirectory(title = "Select directory"): Promise<string | null> {
  if (IS_DESKTOP) {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory: true,
        title,
      });
      return typeof selected === "string" ? selected : null;
    } catch {
      // Fallback to backend-based picker for compatibility.
    }
  }

  // Use raw fetch with a long timeout instead of api.post — the backend
  // blocks while the native OS dialog is open, and api.post's retry logic
  // would open duplicate dialogs if the proxy connection drops.
  const url = IS_DESKTOP
    ? `${await getBackendUrl()}${API.FILES.BROWSE_DIRECTORY}`
    : resolveApiUrl(API.FILES.BROWSE_DIRECTORY);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
    signal: AbortSignal.timeout(600_000), // 10 minutes
  });
  if (!res.ok) throw new Error(`Browse failed: ${res.status}`);
  const result: { path: string | null } = await res.json();
  return result.path;
}

/**
 * Attach files by explicit filesystem paths. No copying.
 * Useful for programmatic attachment or paste-path features.
 */
export async function attachByPath(paths: string[]): Promise<FileAttachment[]> {
  return api.post<FileAttachment[]>(API.FILES.ATTACH, { paths });
}

/**
 * Ingest attached files into the FTS index for an existing session.
 * Called immediately after attaching files so they are indexed
 * without waiting for the next message to be sent.
 */
export async function ingestFiles(
  sessionId: string,
  workspace: string,
  paths: string[],
): Promise<void> {
  try {
    await api.post(API.FILES.INGEST, {
      session_id: sessionId,
      workspace,
      paths,
    });
  } catch (err) {
    // Non-critical — files will still be indexed on next message via prompt.py
    console.warn("FTS ingest failed (will retry on message send):", err);
  }
}

/**
 * Search for files in a workspace directory. Used for @mention autocomplete.
 */
export async function searchFiles(
  directory: string,
  query: string,
): Promise<FileSearchResult[]> {
  return api.post<FileSearchResult[]>(API.FILES.SEARCH, {
    directory,
    query,
    limit: 50,
  });
}
