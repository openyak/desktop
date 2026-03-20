"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { API } from "@/lib/constants";

interface PptxRendererProps {
  filePath?: string;
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

export function PptxRenderer({ filePath }: PptxRendererProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [pptxSource, setPptxSource] = useState<ArrayBuffer | null>(null);
  const blobRef = useRef<Blob | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Dynamically loaded PptxRenderer component
  const [PptxLib, setPptxLib] = useState<{
    PptxRenderer: React.ComponentType<Record<string, unknown>>;
  } | null>(null);

  useEffect(() => {
    if (!filePath) {
      setError("No file path provided");
      setLoading(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch binary content
        const res = await api.post<{
          content_base64: string;
          name: string;
        }>(API.FILES.CONTENT_BINARY, { path: filePath });

        if (cancelled) return;

        setFileName(res.name);
        const buffer = base64ToArrayBuffer(res.content_base64);
        blobRef.current = new Blob([buffer], {
          type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        });

        // Dynamically import pptx-renderer (SSR-safe)
        const pptxModule = await import("@kandiforge/pptx-renderer");

        if (cancelled) return;

        setPptxLib({
          PptxRenderer: pptxModule.PptxRenderer as unknown as React.ComponentType<Record<string, unknown>>,
        });
        setPptxSource(buffer);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load presentation");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [filePath]);

  const handleDownload = useCallback(() => {
    if (!blobRef.current) return;
    const url = URL.createObjectURL(blobRef.current);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName || "presentation.pptx";
    a.click();
    URL.revokeObjectURL(url);
  }, [fileName]);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-[var(--color-destructive)]">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-default)] bg-[var(--surface-tertiary)] shrink-0">
        <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wide truncate">
          {fileName || "presentation.pptx"}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={handleDownload}
          disabled={!blobRef.current}
          title="Download"
        >
          <Download className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Content */}
      <div ref={containerRef} className="flex-1 overflow-auto bg-[var(--surface-secondary)] relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--surface-primary)]">
            <Loader2 className="h-5 w-5 animate-spin text-[var(--text-tertiary)]" />
          </div>
        )}
        {PptxLib && pptxSource && (
          <PptxLib.PptxRenderer
            pptxSource={pptxSource}
            showFilmstrip={true}
            filmstripPosition="bottom"
            showControls={false}
          />
        )}
      </div>
    </div>
  );
}
