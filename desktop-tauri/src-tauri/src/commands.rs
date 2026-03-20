//! Tauri command handlers — the IPC bridge between frontend and Rust.

use tauri::{AppHandle, WebviewWindow};
use tauri_plugin_opener::OpenerExt;

use crate::{backend::BackendState, PendingNavigationState};

/// Get the backend URL (http://127.0.0.1:{port}).
#[tauri::command]
pub async fn get_backend_url(state: tauri::State<'_, BackendState>) -> Result<String, String> {
    Ok(state.url().await)
}

#[tauri::command]
pub async fn get_pending_navigation(
    state: tauri::State<'_, PendingNavigationState>,
) -> Result<Option<String>, String> {
    Ok(state.take().await)
}

/// Minimize the window.
#[tauri::command]
pub fn window_minimize(window: WebviewWindow) -> Result<(), String> {
    window.minimize().map_err(|e| e.to_string())
}

/// Toggle maximize/unmaximize.
#[tauri::command]
pub fn window_maximize(window: WebviewWindow) -> Result<(), String> {
    if window.is_maximized().unwrap_or(false) {
        window.unmaximize().map_err(|e| e.to_string())
    } else {
        window.maximize().map_err(|e| e.to_string())
    }
}

/// Close the window (hides to tray on Windows/Linux).
#[tauri::command]
pub fn window_close(window: WebviewWindow) -> Result<(), String> {
    window.close().map_err(|e| e.to_string())
}

/// Check if window is maximized.
#[tauri::command]
pub fn is_maximized(window: WebviewWindow) -> Result<bool, String> {
    window.is_maximized().map_err(|e| e.to_string())
}

/// Get the current platform.
#[tauri::command]
pub fn get_platform() -> String {
    std::env::consts::OS.to_string()
}

/// Open a URL in the system default browser.
#[tauri::command]
pub fn open_external(app: AppHandle, url: String) -> Result<(), String> {
    app.opener()
        .open_url(url, None::<&str>)
        .map_err(|e| e.to_string())
}

/// Download a file from a URL and save it via a native save dialog.
///
/// WebView2 does not support blob-URL downloads triggered by `<a>.click()`,
/// so we handle PDF (and other file) exports through Tauri IPC instead.
#[tauri::command]
pub async fn download_and_save(
    app: AppHandle,
    url: String,
    default_name: String,
) -> Result<bool, String> {
    use tauri_plugin_dialog::DialogExt;

    // Show native save dialog first (instant — no waiting for download)
    let (tx, rx) = tokio::sync::oneshot::channel();
    app.dialog()
        .file()
        .set_file_name(&default_name)
        .add_filter("PDF", &["pdf"])
        .save_file(move |path| {
            let _ = tx.send(path);
        });

    let file_path = rx.await.map_err(|e| format!("Dialog error: {e}"))?;
    let path = match file_path {
        Some(p) => p,
        None => return Ok(false), // User cancelled
    };

    // Download the file from the local backend
    let response = reqwest::get(&url)
        .await
        .map_err(|e| format!("Download failed: {e}"))?;
    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read response: {e}"))?;

    // Write to the chosen path
    let real_path = path
        .as_path()
        .ok_or_else(|| "Invalid save path".to_string())?;
    tokio::fs::write(real_path, &bytes)
        .await
        .map_err(|e| format!("Failed to write file: {e}"))?;

    Ok(true)
}
