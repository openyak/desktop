/**
 * Global type declarations for the desktop API.
 *
 * Augments the Window interface to include desktop-specific APIs
 * for both Tauri and legacy Electron environments.
 */

interface Window {
  electronAPI?: {
    getBackendUrl: () => Promise<string>;
    getPlatform: () => string;
    minimize: () => void;
    maximize: () => void;
    close: () => void;
    isMaximized: () => Promise<boolean>;
    onMaximizeChange: (callback: (maximized: boolean) => void) => () => void;
    showOpenDialog: (
      options: {
        title?: string;
        defaultPath?: string;
        filters?: { name: string; extensions: string[] }[];
        properties?: string[];
      }
    ) => Promise<{ canceled: boolean; filePaths: string[] }>;
    onBackendRestart: (callback: (newUrl: string) => void) => () => void;
  };
  __TAURI_INTERNALS__?: unknown;
}
