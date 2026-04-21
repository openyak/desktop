"use client";

import { useState, useRef, useEffect, useCallback, memo } from "react";
import { useTranslation } from 'react-i18next';
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2, Pencil, FileDown, FileText, Pin, PinOff, MessageCircle, EllipsisVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import { getChatRoute } from "@/lib/routes";
import { useDebouncedPrefetch } from "@/hooks/use-debounced-prefetch";
import type { PaginatedMessages } from "@/types/message";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import type { SessionResponse } from "@/types/session";

interface SessionItemProps {
  session: SessionResponse;
  isActive?: boolean;
  onDelete: (id: string, title: string) => void;
  onRename: (id: string, newTitle: string) => void;
  onExportPdf?: (id: string, title: string) => void;
  onExportMarkdown?: (id: string, title: string) => void;
  onTogglePin?: (id: string, pinned: boolean) => void;
  isEditing?: boolean;
  onEditStart?: (id: string) => void;
  onEditEnd?: () => void;
  snippet?: string;
  isFocused?: boolean;
  /** Extra left indent, used when the row sits under a project group header */
  indent?: boolean;
}

export const SessionItem = memo(function SessionItem({
  session,
  isActive = false,
  onDelete,
  onRename,
  onExportPdf,
  onExportMarkdown,
  onTogglePin,
  isEditing = false,
  onEditStart,
  onEditEnd,
  snippet,
  isFocused = false,
  indent = false,
}: SessionItemProps) {
  const { t } = useTranslation('common');
  const router = useRouter();
  const queryClient = useQueryClient();
  const { prefetch, cancel } = useDebouncedPrefetch(150);
  const [editValue, setEditValue] = useState("");
  const [scrollVars, setScrollVars] = useState<React.CSSProperties | undefined>();
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLParagraphElement>(null);

  const rawTitle = session.title || t('newConversation');
  // Clean up ugly channel titles: "Channel: whatsapp:+1234567890" → "+1234567890"
  const title = rawTitle.startsWith("Channel: ")
    ? rawTitle.slice(9).replace(/^(whatsapp|discord|telegram|slack|feishu|signal|line|imessage):/, "")
    : rawTitle;
  const relativeTime = getRelativeTimeLabel(session.time_updated, t);
  const channelBadge = session.slug ? getChannelBadge(session.slug) : null;

  // Focus the item when it receives roving tabindex focus
  useEffect(() => {
    if (isFocused && !isEditing && itemRef.current) {
      itemRef.current.focus();
    }
  }, [isFocused, isEditing]);

  // Focus and select input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      setEditValue(title);
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [isEditing, title]);

  // Measure title overflow once on mount / title change
  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    if (el.scrollWidth > el.clientWidth) {
      const dist = el.scrollWidth - el.clientWidth;
      setScrollVars({
        '--scroll-distance': `-${dist}px`,
        '--scroll-duration': `${dist / 50}s`,
      } as React.CSSProperties);
    } else {
      setScrollVars(undefined);
    }
  }, [title]);

  const handleSubmitRename = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== title) {
      onRename(session.id, trimmed);
    }
    onEditEnd?.();
  }, [editValue, title, session.id, onRename, onEditEnd]);

  const handleCancelRename = useCallback(() => {
    setEditValue(title);
    onEditEnd?.();
  }, [title, onEditEnd]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSubmitRename();
      } else if (e.key === "Escape") {
        e.preventDefault();
        handleCancelRename();
      }
    },
    [handleSubmitRename, handleCancelRename],
  );

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          ref={itemRef}
          role="option"
          aria-selected={isActive}
          tabIndex={isFocused ? 0 : -1}
          onClick={() => !isEditing && router.push(getChatRoute(session.id))}
          onKeyDown={(e) => !isEditing && e.key === "Enter" && router.push(getChatRoute(session.id))}
          onMouseEnter={() => {
            prefetch(() => {
              const isCached = queryClient.getQueryData(queryKeys.messages.list(session.id));
              if (!isCached) {
                queryClient.prefetchInfiniteQuery({
                  queryKey: queryKeys.messages.list(session.id),
                  queryFn: () => api.get<PaginatedMessages>(API.MESSAGES.LIST(session.id, 50, -1)),
                  initialPageParam: -1,
                  staleTime: 60_000,
                });
              }
            });
          }}
          onMouseLeave={() => {
            cancel();
          }}
          className={cn(
            "group relative mx-3 flex cursor-pointer items-center gap-2 overflow-hidden rounded-lg text-sm transition-colors duration-150 ease-out",
            indent ? "pl-9 pr-2" : "px-3",
            snippet ? "py-1.5" : "py-1",
            isActive
              ? "bg-[var(--sidebar-active)] text-[var(--text-primary)] shadow-[var(--sidebar-active-shadow)]"
              : "text-[var(--text-primary)] hover:bg-[var(--sidebar-hover)]",
            isEditing && "ring-1 ring-[var(--brand-primary)]",
          )}
        >
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <input
                ref={inputRef}
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleSubmitRename}
                onClick={(e) => e.stopPropagation()}
                className="w-full border-b border-[var(--brand-primary)] bg-transparent py-0.5 text-sm text-[var(--text-primary)] outline-none"
              />
            ) : (
              <>
                <p
                  ref={titleRef}
                  className="flex items-center gap-1.5 overflow-hidden whitespace-nowrap text-sm leading-5"
                  style={scrollVars}
                >
                  {channelBadge && (
                    <MessageCircle className={cn("inline h-3 w-3 shrink-0", channelBadge.color)} />
                  )}
                  <span
                    className={cn(
                      "min-w-0 flex-1 overflow-hidden text-ellipsis",
                      scrollVars ? "inline-block group-hover:animate-scroll-text" : "",
                    )}
                  >
                    {title}
                  </span>
                </p>
                {snippet && (
                  <p className="mt-0.5 truncate text-ui-2xs leading-4 text-[var(--text-tertiary)]">
                    …{snippet}…
                  </p>
                )}
              </>
            )}
          </div>

          {/* Right-side slot: relative time (fades out on hover), three-dot menu (fades in) */}
          {!isEditing && (
            <>
              <span
                aria-hidden
                className="ml-auto shrink-0 text-ui-2xs text-[var(--text-tertiary)] opacity-100 transition-opacity group-hover:opacity-0"
              >
                {relativeTime}
              </span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  onClick={(e) => e.stopPropagation()}
                  className="absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-[var(--text-tertiary)] opacity-0 transition-opacity hover:bg-[var(--surface-tertiary)] hover:text-[var(--text-primary)] focus:opacity-100 group-hover:opacity-100 data-[state=open]:opacity-100"
                >
                  <EllipsisVertical className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-44" align="start" side="right">
                <DropdownMenuItem onSelect={() => onTogglePin?.(session.id, !session.is_pinned)}>
                  {session.is_pinned ? (
                    <><PinOff className="h-3.5 w-3.5" />{t('unpin', { defaultValue: 'Unpin' })}</>
                  ) : (
                    <><Pin className="h-3.5 w-3.5" />{t('pin', { defaultValue: 'Pin' })}</>
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onEditStart?.(session.id)}>
                  <Pencil className="h-3.5 w-3.5" />
                  {t('rename')}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onExportPdf?.(session.id, title)}>
                  <FileDown className="h-3.5 w-3.5" />
                  {t('exportPdf')}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onExportMarkdown?.(session.id, title)}>
                  <FileText className="h-3.5 w-3.5" />
                  {t('exportMarkdown', { defaultValue: 'Export Markdown' })}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={() => onDelete(session.id, title)}
                  className="text-[var(--color-destructive)] focus:text-[var(--color-destructive)]"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {t('delete')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            </>
          )}
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent className="w-44">
        <ContextMenuItem onSelect={() => onTogglePin?.(session.id, !session.is_pinned)}>
          {session.is_pinned ? (
            <><PinOff className="h-3.5 w-3.5" />{t('unpin', { defaultValue: 'Unpin' })}</>
          ) : (
            <><Pin className="h-3.5 w-3.5" />{t('pin', { defaultValue: 'Pin' })}</>
          )}
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => onEditStart?.(session.id)}>
          <Pencil className="h-3.5 w-3.5" />
          {t('rename')}
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => onExportPdf?.(session.id, title)}>
          <FileDown className="h-3.5 w-3.5" />
          {t('exportPdf')}
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => onExportMarkdown?.(session.id, title)}>
          <FileText className="h-3.5 w-3.5" />
          {t('exportMarkdown', { defaultValue: 'Export Markdown' })}
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          onSelect={() => onDelete(session.id, title)}
          className="text-[var(--color-destructive)] focus:text-[var(--color-destructive)]"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t('delete')}
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
});

function getRelativeTimeLabel(date: string, t: (key: string, options?: Record<string, unknown>) => string) {
  const now = new Date();
  const d = new Date(date);
  const diff = now.getTime() - d.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return t("justNow");
  if (minutes < 60) return t("minutesAgo", { count: minutes });
  if (hours < 24) return t("hoursAgo", { count: hours });
  if (days < 7) return t("daysAgo", { count: days });

  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: d.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

/** Map session slug prefix to a channel badge. */
function getChannelBadge(slug: string): { label: string; color: string } | null {
  if (!slug) return null;
  const prefix = slug.split(":")[0];
  switch (prefix) {
    case "whatsapp": return { label: "WhatsApp", color: "text-emerald-500" };
    case "discord":  return { label: "Discord",  color: "text-indigo-400" };
    case "telegram": return { label: "Telegram", color: "text-sky-400" };
    case "feishu":   return { label: "Feishu",   color: "text-blue-500" };
    case "slack":    return { label: "Slack",    color: "text-purple-400" };
    case "wechat":   return { label: "WeChat",   color: "text-green-500" };
    case "signal":   return { label: "Signal",   color: "text-blue-400" };
    case "line":     return { label: "LINE",     color: "text-green-400" };
    default: return slug.includes(":") ? { label: prefix, color: "text-[var(--text-tertiary)]" } : null;
  }
}
