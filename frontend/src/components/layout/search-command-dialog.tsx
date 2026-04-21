"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { MessageSquareText, Search } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useSessions, useSearchSessions } from "@/hooks/use-sessions";
import { IS_DESKTOP, TITLE_BAR_HEIGHT } from "@/lib/constants";
import { getChatRoute } from "@/lib/routes";
import { directoryLabelOf } from "@/lib/utils";
import { useSidebarStore } from "@/stores/sidebar-store";
import type { SessionResponse } from "@/types/session";

const KBD_SHORTCUT_COUNT = 5;
const RECENT_LIMIT = 10;
const MAX_RESULTS = 30;

interface Row {
  session: SessionResponse;
  snippet?: string | null;
}

export function SearchCommandDialog() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const open = useSidebarStore((s) => s.isSearchModalOpen);
  const setOpen = useSidebarStore((s) => s.setSearchModalOpen);
  const [query, setQuery] = useState("");

  const { data: sessionPages } = useSessions();
  const { data: searchResults } = useSearchSessions(query);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  // Global ⌘K / Ctrl+K opens the palette from anywhere in the app.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const modKey = e.metaKey || e.ctrlKey;
      if (!modKey || e.shiftKey || e.altKey) return;
      if (e.key !== "k" && e.key !== "K") return;
      const target = e.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;
      if (typing && !open) return;
      e.preventDefault();
      setOpen(!useSidebarStore.getState().isSearchModalOpen);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const rows = useMemo<Row[]>(() => {
    const trimmed = query.trim();
    const all = sessionPages?.pages.flat() ?? [];

    if (trimmed.length >= 2 && searchResults) {
      return searchResults
        .slice(0, MAX_RESULTS)
        .map((r) => ({ session: r.session, snippet: r.snippet }));
    }

    if (trimmed.length > 0) {
      const q = trimmed.toLowerCase();
      return all
        .filter((s) => (s.title ?? "").toLowerCase().includes(q))
        .slice(0, MAX_RESULTS)
        .map((s) => ({ session: s }));
    }

    return all.slice(0, RECENT_LIMIT).map((s) => ({ session: s }));
  }, [query, sessionPages, searchResults]);

  const navigate = (session: SessionResponse) => {
    router.push(getChatRoute(session.id));
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      const modKey = e.metaKey || e.ctrlKey;
      if (!modKey) return;
      if (!/^[1-9]$/.test(e.key)) return;
      const idx = parseInt(e.key, 10) - 1;
      const row = rows[idx];
      if (!row) return;
      e.preventDefault();
      navigate(row.session);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // navigate is stable enough for this lifetime
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rows]);

  const hasQuery = query.trim().length > 0;
  const desktopTopOffset = TITLE_BAR_HEIGHT + 48;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="top-[96px] max-w-[640px] translate-y-0 gap-0 overflow-hidden rounded-2xl border border-[var(--border-default)] bg-[var(--surface-primary)] p-0 shadow-[var(--shadow-lg)] data-[state=closed]:slide-out-to-top-[96px] data-[state=open]:slide-in-from-top-[96px] [&>button]:hidden"
        style={IS_DESKTOP ? { top: desktopTopOffset } : undefined}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogTitle className="sr-only">{t("searchChats")}</DialogTitle>
        <Command shouldFilter={false} className="bg-transparent">
          <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
            <Search className="h-[14px] w-[14px] shrink-0 text-[var(--text-tertiary)]" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("searchChats")}
              className="flex-1 bg-transparent text-base text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none"
            />
          </div>
          <CommandList className="max-h-[420px] p-1">
            {rows.length === 0 ? (
              <CommandEmpty>{t("noMatchingConversations")}</CommandEmpty>
            ) : (
              <CommandGroup
                heading={hasQuery ? t("searchResults") : t("recentChats")}
                className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:text-ui-3xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.12em] [&_[cmdk-group-heading]]:text-[var(--text-tertiary)]"
              >
                {rows.map((row, i) => {
                  const { session, snippet } = row;
                  const label =
                    session.directory && session.directory !== "."
                      ? directoryLabelOf(session.directory)
                      : null;
                  const title = session.title || t("newConversation");
                  return (
                    <CommandItem
                      key={session.id}
                      value={`${session.id} ${title}`}
                      onSelect={() => navigate(session)}
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] data-[selected=true]:bg-[var(--sidebar-hover)] data-[selected=true]:text-[var(--text-primary)]"
                    >
                      <MessageSquareText className="h-3.5 w-3.5 shrink-0 text-[var(--text-tertiary)]" />
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate">{title}</span>
                        {snippet && (
                          <span className="truncate text-ui-2xs text-[var(--text-tertiary)]">
                            …{snippet}…
                          </span>
                        )}
                      </div>
                      {label && (
                        <span className="shrink-0 text-ui-2xs text-[var(--text-tertiary)]">
                          {label}
                        </span>
                      )}
                      {i < KBD_SHORTCUT_COUNT && !hasQuery && (
                        <kbd className="shrink-0 rounded border border-[var(--border-default)] px-1.5 py-0.5 text-ui-3xs font-normal text-[var(--text-tertiary)]">
                          ⌘{i + 1}
                        </kbd>
                      )}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
