"use client";

import { useMemo, useRef, useState, useCallback, useEffect } from "react";
import { RotateCw, Code, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TryFixButton } from "../try-fix-button";

interface ReactRendererProps {
  code: string;
  title?: string;
}

/** HTML template for the sandboxed React iframe. */
function buildSrcDoc(code: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://unpkg.com/react@19/umd/react.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@19/umd/react-dom.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; }
    #root { min-height: 100vh; }
    #error { color: #ef4444; padding: 16px; font-family: monospace; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="error" style="display:none"></div>
  <script type="text/babel" data-type="module">
    function reportError(msg) {
      document.getElementById('error').style.display = 'block';
      document.getElementById('error').textContent = msg;
      try { window.parent.postMessage({ type: 'artifact-error', error: msg }, '*'); } catch(e) {}
    }
    try {
      ${code}

      // Find the default export
      const Component = typeof App !== 'undefined' ? App
        : typeof Default !== 'undefined' ? Default
        : null;

      if (Component) {
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(React.createElement(Component));
      } else {
        reportError('No component found. Export a default function component or define an App function.');
      }
    } catch (err) {
      reportError(err.message + '\\n' + err.stack);
    }
  </script>
</body>
</html>`;
}

export function ReactRenderer({ code, title }: ReactRendererProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [showSource, setShowSource] = useState(false);
  const [key, setKey] = useState(0);
  const [iframeError, setIframeError] = useState<string | null>(null);

  const srcDoc = useMemo(() => buildSrcDoc(code), [code]);

  const refresh = useCallback(() => {
    setIframeError(null);
    setKey((k) => k + 1);
  }, []);

  // Listen for error messages from the iframe
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === "artifact-error" && typeof e.data.error === "string") {
        setIframeError(e.data.error);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  // Clear error when code changes
  useEffect(() => {
    setIframeError(null);
  }, [code]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-default)] bg-[var(--surface-tertiary)] shrink-0">
        <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">
          {showSource ? "Source" : "Preview"}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowSource(!showSource)}
            title={showSource ? "Show preview" : "Show source"}
          >
            {showSource ? <Eye className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
          </Button>
          {!showSource && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={refresh}
              title="Refresh"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      {showSource ? (
        <pre className="flex-1 overflow-auto p-4 text-[13px] leading-relaxed font-mono text-[var(--text-primary)] bg-[var(--surface-secondary)]">
          {code}
        </pre>
      ) : (
        <div className="flex-1 flex flex-col relative">
          <iframe
            key={key}
            ref={iframeRef}
            srcDoc={srcDoc}
            sandbox="allow-scripts"
            title={title || "React Preview"}
            className="flex-1 w-full border-0 bg-white"
          />
          {iframeError && (
            <div className="absolute bottom-0 left-0 right-0 bg-[var(--surface-primary)] border-t border-[var(--border-default)] px-4 py-3">
              <TryFixButton error={iframeError} artifactType="React component" artifactTitle={title} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
