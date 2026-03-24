"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from 'react-i18next';
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2, Pencil, MoreHorizontal, FileDown, FileText, FolderOpen, Pin, PinOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { API, queryKeys } from "@/lib/constants";
import { getChatRoute, resolveSessionId } from "@/lib/routes";
import { useDebouncedPrefetch } from "@/hooks/use-debounced-prefetch";
import type { PaginatedMessages } from "@/types/message";
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
}

export function SessionItem({
  session,
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
}: SessionItemProps) {
  const { t } = useTranslation('common');
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { prefetch, cancel } = useDebouncedPrefetch(150);
  const activeSessionId = resolveSessionId(
    typeof params.sessionId === "string" ? params.sessionId : null,
    searchParams.get("sessionId"),
  );
  const isActive = activeSessionId === session.id;
  const [hovered, setHovered] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRef = useRef<HTMLDivElement>(null);

  const title = session.title || t('newConversation');
  const showActions = (isActive || hovered || menuOpen) && !isEditing;

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
      // Use requestAnimationFrame to ensure the input is rendered
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [isEditing, title]);

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
    <div
      ref={itemRef}
      role="option"
      aria-selected={isActive}
      tabIndex={isFocused ? 0 : -1}
      onClick={() => !isEditing && router.push(getChatRoute(session.id))}
      onKeyDown={(e) => !isEditing && e.key === "Enter" && router.push(getChatRoute(session.id))}
      onMouseEnter={() => {
        setHovered(true);
        // Debounced prefetch - only fetch after 300ms of hover
        // Skip if already cached to avoid unnecessary requests
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
        setHovered(false);
        cancel(); // Cancel pending prefetch
      }}
      className={cn(
        "relative flex items-center overflow-hidden rounded-xl px-3 py-3 mx-2 text-[13px] cursor-pointer transition-all duration-150",
        isActive
          ? "bg-[var(--sidebar-active)] text-[var(--text-primary)] before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-0.5 before:rounded-full before:bg-[var(--text-primary)]"
          : "text-[var(--text-secondary)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)]",
        isEditing && "ring-1 ring-[var(--brand-primary)]",
      )}
    >

      <div className="flex-1 min-w-0">
        {isEditing ? (
          <div className="flex items-center gap-1">
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleSubmitRename}
              onClick={(e) => e.stopPropagation()}
              className="w-full bg-transparent text-sm text-[var(--text-primary)] outline-none border-b border-[var(--brand-primary)] py-0.5"
            />
          </div>
        ) : (
          <>
            <p className="truncate pr-2">{title}</p>
            {session.directory && session.directory !== "." && !snippet && (
              <p className="truncate pr-2 text-[11px] text-[var(--text-tertiary)] mt-0.5 flex items-center gap-1">
                <FolderOpen className="inline h-3 w-3 shrink-0" />
                {session.directory.replace(/\\/g, "/").replace(/\/$/, "").split("/").pop()}
              </p>
            )}
            {snippet && (
              <p className="truncate pr-2 text-[11px] text-[var(--text-tertiary)] mt-0.5">
                …{snippet}…
              </p>
            )}
          </>
        )}
      </div>

      <div
        className={cn(
          "absolute right-1 inset-y-0 flex items-center transition-opacity duration-150",
          showActions ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
      >
          <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center justify-center w-7 h-7 rounded-lg transition-colors text-[var(--text-primary)] hover:bg-[var(--surface-tertiary)]"
                aria-label="More options"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onTogglePin?.(session.id, !session.is_pinned);
                }}
              >
                {session.is_pinned ? (
                  <><PinOff className="h-3.5 w-3.5" />{t('unpin', { defaultValue: 'Unpin' })}</>
                ) : (
                  <><Pin className="h-3.5 w-3.5" />{t('pin', { defaultValue: 'Pin' })}</>
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onEditStart?.(session.id);
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
                {t('rename')}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onExportPdf?.(session.id, title);
                }}
              >
                <FileDown className="h-3.5 w-3.5" />
                {t('exportPdf')}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onExportMarkdown?.(session.id, title);
                }}
              >
                <FileText className="h-3.5 w-3.5" />
                {t('exportMarkdown', { defaultValue: 'Export Markdown' })}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(session.id, title);
                }}
                className="text-[var(--color-destructive)] focus:text-[var(--color-destructive)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
                {t('delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
      </div>
    </div>
  );
}
