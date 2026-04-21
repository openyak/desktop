"use client";

import { useEffect, useRef, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Mail, FileDiff, CalendarDays, Settings,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslation } from 'react-i18next';
import { ChatForm } from "./chat-form";
import { ChatHeader } from "./chat-header";
import { OfflineOverlay } from "@/components/layout/offline-overlay";
import { StreamingMessage } from "@/components/messages/assistant-message";
import { FileChip } from "./file-chip";
import { useChat } from "@/hooks/use-chat";
import { useChatStore } from "@/stores/chat-store";
import { useArtifactStore } from "@/stores/artifact-store";
import { useActivityStore } from "@/stores/activity-store";
import { useSettingsStore } from "@/stores/settings-store";

const FEATURED_STARTERS = [
  { icon: Mail, textKey: "starterDraftFromNotes", promptKey: "starterDraftFromNotesPrompt" },
  { icon: FileDiff, textKey: "starterCompareDocs", promptKey: "starterCompareDocsPrompt" },
  { icon: CalendarDays, textKey: "starterWeeklyDigest", promptKey: "starterWeeklyDigestPrompt" },
];

export function Landing() {
  const { t } = useTranslation('chat');
  const { sendMessage, isGenerating, stopGeneration, pendingUserText, pendingAttachments, streamingParts, streamingText, streamingReasoning } = useChat();
  const globalWorkspace = useSettingsStore((s) => s.workspaceDirectory);
  const activeProvider = useSettingsStore((s) => s.activeProvider);
  const searchParams = useSearchParams();
  const directoryParam = searchParams?.get("directory") ?? null;
  const starters = useMemo(() => FEATURED_STARTERS.slice(0, 2), []);

  useEffect(() => {
    const state = useChatStore.getState();
    if (!state.isGenerating) {
      state.reset();
    }
    // Respect ?directory=... (used by "Add new project"); otherwise start unrestricted.
    useSettingsStore.getState().setWorkspaceDirectory(directoryParam || null);
    // Close right-side panels when landing page mounts (new chat / after delete)
    useArtifactStore.getState().clearAll();
    useActivityStore.getState().close();
  }, [directoryParam]);

  // Capture the user text in local state so it persists even after
  // startGeneration() clears pendingUserText from the global store.
  // This prevents the user bubble from flashing away before navigation.
  const capturedTextRef = useRef<string | null>(null);
  if (pendingUserText) {
    capturedTextRef.current = pendingUserText;
  }
  if (!isGenerating) {
    capturedTextRef.current = null;
  }
  const displayText = pendingUserText ?? capturedTextRef.current;

  // When generating, switch to a chat-like layout — uses the same
  // StreamingMessage component as chat-view for visual consistency.
  if (isGenerating) {
    return (
      <div className="relative flex flex-1 flex-col h-full overflow-hidden">
        <OfflineOverlay />
        <ChatHeader />

        {/* Messages area — optimistic user bubble + streaming assistant */}
        <div className="flex-1 overflow-y-auto">
          {displayText && (
            <div className="px-4 py-3">
              <div className="mx-auto max-w-3xl xl:max-w-4xl">
                <motion.div
                  className="flex justify-end"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="max-w-[85%] sm:max-w-[70%] rounded-2xl bg-[var(--user-bubble-bg)] px-4 py-2.5 shadow-[var(--shadow-sm)] border border-[var(--border-default)]">
                    <div className="text-[13px] text-[var(--text-primary)] whitespace-pre-wrap break-words leading-relaxed">
                      {displayText}
                    </div>
                    {pendingAttachments && pendingAttachments.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {pendingAttachments.map((att) => (
                          <FileChip key={att.file_id} file={att} />
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              </div>
            </div>
          )}

          {/* Streaming assistant message — same component used in chat-view */}
          <div className="px-4 py-5">
            <div className="mx-auto max-w-3xl xl:max-w-4xl">
              <StreamingMessage
                parts={streamingParts}
                streamingText={streamingText}
                streamingReasoning={streamingReasoning}
              />
            </div>
          </div>
        </div>

        {/* Input */}
        <ChatForm
          isGenerating={isGenerating}
          onSend={sendMessage}
          onStop={stopGeneration}
          directory={globalWorkspace}
        />
      </div>
    );
  }

  return (
    <div className="relative flex flex-1 flex-col h-full overflow-hidden">
      <OfflineOverlay />
      <ChatHeader />

      <div className="flex flex-1 flex-col items-center justify-center px-4 pb-8">
        <div className="w-full max-w-3xl xl:max-w-4xl space-y-8">
          {/* Provider setup prompt */}
          {!activeProvider && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
              className="flex items-center gap-4 rounded-xl border border-[var(--brand-primary)]/30 bg-[var(--brand-primary)]/5 px-5 py-4"
            >
              <Settings className="h-5 w-5 shrink-0 text-[var(--brand-primary)]" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {t('setupProvider')}
                </p>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  {t('setupProviderDesc')}
                </p>
              </div>
              <Link
                href="/settings?tab=providers"
                className="shrink-0 inline-flex items-center rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--surface-secondary)] transition-colors"
              >
                {t('configureSettings')}
              </Link>
            </motion.div>
          )}

          {/* Greeting */}
          <div className="text-center pb-2 space-y-2">
            <h1 className="text-3xl sm:text-[2.5rem] font-medium text-[var(--text-primary)] tracking-tight">
              {t('greeting')}
            </h1>
            <p className="text-sm text-[var(--text-secondary)] max-w-2xl mx-auto">
              {t('subtitle')}
            </p>
          </div>

          {/* Input — the focal point */}
          <ChatForm
            isGenerating={isGenerating}
            onSend={sendMessage}
            onStop={stopGeneration}
            directory={globalWorkspace}
          />

          {/* Recommendation chips — intentionally capped at two */}
          <div className="space-y-3 pt-1">
            <p className="text-center text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
              {t("recommendedActions")}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
            {starters.map((starter) => (
              <button
                key={starter.textKey}
                onClick={() => useArtifactStore.getState().requestFix(t(starter.promptKey))}
                disabled={isGenerating}
                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-default)] px-4 py-2 text-[13px] font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-heavy)] hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
              >
                <starter.icon className="h-3.5 w-3.5 shrink-0" />
                <span>{t(starter.textKey)}</span>
              </button>
            ))}
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}
