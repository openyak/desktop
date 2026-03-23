"use client";

import { useState, useEffect, useRef } from "react";
import { ShieldAlert, ShieldCheck, ShieldX, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { PERMISSION_TIMEOUT } from "@/lib/constants";
import { isRemoteMode } from "@/lib/remote-connection";
import { useSettingsStore } from "@/stores/settings-store";
import type { PermissionRequest } from "@/types/streaming";

interface PermissionDialogProps {
  permission: PermissionRequest;
  onRespond: (allow: boolean) => void;
}

const TOOL_EXPLANATIONS: Record<string, {
  action: string;
  impact: string;
  safeguard: string;
}> = {
  read: {
    action: "Read files from your selected workspace",
    impact: "No files will be modified",
    safeguard: "You can deny if the path looks unrelated",
  },
  write: {
    action: "Create or overwrite a file",
    impact: "File content will change on disk",
    safeguard: "Allow only when the target file/path is expected",
  },
  edit: {
    action: "Edit an existing file",
    impact: "Existing content may be replaced",
    safeguard: "Allow only for files you intend to update now",
  },
  bash: {
    action: "Run a shell command",
    impact: "May change files or system state",
    safeguard: "Deny if command scope is unclear",
  },
  web_fetch: {
    action: "Fetch content from a URL",
    impact: "No local files changed",
    safeguard: "Allow trusted domains only",
  },
};

function getToolExplanation(tool: string) {
  return TOOL_EXPLANATIONS[tool] ?? {
    action: "Run a tool action",
    impact: "May read or modify workspace data",
    safeguard: "Review details before allowing",
  };
}

/** Send a browser notification if tab is not focused. */
function notifyIfHidden(tool: string) {
  if (typeof document === "undefined" || document.visibilityState !== "hidden") return;
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  try {
    new Notification("OpenYak — Permission Required", {
      body: `The assistant wants to use ${tool} and needs your approval.`,
      tag: "openyak-permission", // deduplicate
    });
  } catch {
    // Notifications may not be supported in all contexts
  }
}

/** Request notification permission on first render (one-time). */
function useRequestNotificationPermission() {
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);
}

export function PermissionDialog({ permission, onRespond }: PermissionDialogProps) {
  const [remainingMs, setRemainingMs] = useState(PERMISSION_TIMEOUT);
  const [rememberChoice, setRememberChoice] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const startTimeRef = useRef(Date.now());
  const expired = remainingMs <= 0;
  const hasDeniedRef = useRef(false);
  const savePermissionRule = useSettingsStore((s) => s.savePermissionRule);
  const displayTool = permission.tool || permission.permission || "this action";
  const details = getToolExplanation(permission.tool || permission.permission);
  const isMobile = isRemoteMode();

  useRequestNotificationPermission();

  const handleRespond = async (allow: boolean) => {
    if (submitting) return;
    setSubmitting(true);
    if (rememberChoice) {
      savePermissionRule(permission.tool || permission.permission, allow);
    }
    try {
      await onRespond(allow);
    } finally {
      setSubmitting(false);
    }
  };

  // Send browser notification when permission request appears
  useEffect(() => {
    notifyIfHidden(permission.tool);
  }, [permission.tool]);

  useEffect(() => {
    setSubmitting(false);
    hasDeniedRef.current = false;
  }, [permission.callId]);

  // Countdown timer
  useEffect(() => {
    startTimeRef.current = Date.now();
    setRemainingMs(PERMISSION_TIMEOUT);

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      const remaining = PERMISSION_TIMEOUT - elapsed;
      setRemainingMs(Math.max(0, remaining));
      if (remaining <= 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [permission.callId]);

  useEffect(() => {
    if (expired && !hasDeniedRef.current) {
      hasDeniedRef.current = true;
      handleRespond(false);
    }
  }, [expired, handleRespond]);

  const remainingSec = Math.ceil(remainingMs / 1000);
  const remainingMin = Math.floor(remainingSec / 60);
  const remainingSecPart = remainingSec % 60;
  const timeStr = `${remainingMin}:${String(remainingSecPart).padStart(2, "0")}`;

  // Show warning when < 60s remaining
  const isUrgent = remainingSec <= 60 && !expired;

  // Mobile: bottom-sheet style anchored to bottom
  if (isMobile) {
    return (
      <div className="px-3 pb-[max(env(safe-area-inset-bottom),8px)]">
        <div className="rounded-2xl border-2 border-[var(--color-warning)]/40 bg-[var(--surface-primary)] shadow-lg p-4 animate-slide-up">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-[var(--color-warning)]" />
                <h3 className="text-base font-semibold text-[var(--text-primary)]">
                  Permission Required
                </h3>
              </div>
              {!expired && (
                <span className={`flex items-center gap-1 text-xs tabular-nums ${
                  isUrgent ? "text-[var(--color-destructive)]" : "text-[var(--text-tertiary)]"
                }`}>
                  <Clock className="h-3.5 w-3.5" />
                  {timeStr}
                </span>
              )}
            </div>

            {expired ? (
              <p className="text-sm text-[var(--color-destructive)]">
                This permission request has timed out.
              </p>
            ) : (
              <div className="text-sm text-[var(--text-secondary)] space-y-1">
                <p>
                  Wants to use <span className="font-medium text-[var(--text-primary)]">{displayTool}</span>
                </p>
                <p className="text-xs">{details.action} &middot; {details.impact}</p>
              </div>
            )}

            {!expired && permission.patterns.length > 0 && (
              <div className="rounded-xl bg-[var(--surface-secondary)] border border-[var(--border-default)] p-3">
                <p className="text-[10px] text-[var(--text-tertiary)] uppercase font-semibold mb-1">
                  Details
                </p>
                <div className="space-y-0.5">
                  {permission.patterns.map((p, i) => (
                    <p key={i} className="text-sm text-[var(--text-secondary)] break-all">
                      {p}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {!expired && (
              <>
                <div className="flex items-center gap-2 py-2 border-t border-[var(--border-default)]">
                  <Switch
                    checked={rememberChoice}
                    onCheckedChange={setRememberChoice}
                    id="remember-choice-mobile"
                  />
                  <label
                    htmlFor="remember-choice-mobile"
                    className="text-sm text-[var(--text-secondary)] cursor-pointer select-none"
                  >
                    Remember for <span className="font-medium text-[var(--text-primary)]">{displayTool}</span>
                  </label>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void handleRespond(false)}
                    disabled={submitting}
                    className="flex-1 h-12 flex items-center justify-center gap-2 rounded-xl border-2 border-[var(--border-default)] bg-[var(--surface-secondary)] text-[var(--text-primary)] text-base font-medium active:scale-[0.97] transition-all disabled:opacity-50"
                  >
                    <ShieldX className="h-5 w-5" />
                    Deny
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleRespond(true)}
                    disabled={submitting}
                    className="flex-1 h-12 flex items-center justify-center gap-2 rounded-xl bg-[var(--text-primary)] text-[var(--surface-primary)] text-base font-medium active:scale-[0.97] transition-all disabled:opacity-50"
                  >
                    <ShieldCheck className="h-5 w-5" />
                    Allow
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Desktop layout (unchanged)
  return (
    <div className="px-4 pb-3">
      <div className="mx-auto max-w-3xl xl:max-w-4xl">
        <div className="rounded-xl border-2 border-[var(--color-warning)]/40 bg-[var(--color-warning)]/5 p-4 animate-slide-up">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-[var(--color-warning)] shrink-0 mt-0.5" />
            <div className="flex-1 space-y-3">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Permission Required
                  </h3>
                  {!expired && (
                    <span className={`flex items-center gap-1 text-[11px] tabular-nums ${
                      isUrgent ? "text-[var(--color-destructive)]" : "text-[var(--text-tertiary)]"
                    }`}>
                      <Clock className="h-3 w-3" />
                      {timeStr}
                    </span>
                  )}
                </div>
                {expired ? (
                  <p className="text-xs text-[var(--color-destructive)] mt-1">
                    This permission request has timed out. The agent will continue without this action.
                  </p>
                ) : (
                  <div className="text-xs text-[var(--text-secondary)] mt-1 space-y-1">
                    <p>
                       The assistant wants to use <span className="font-medium">{displayTool}</span>.
                    </p>
                    <p>Will do: {details.action}</p>
                    <p>Impact: {details.impact}</p>
                    <p>Tip: {details.safeguard}</p>
                  </div>
                )}
              </div>

              {!expired && permission.patterns.length > 0 && (
                <div className="rounded-lg bg-[var(--surface-secondary)] border border-[var(--border-default)] p-2.5">
                  <p className="text-[10px] text-[var(--text-tertiary)] uppercase font-semibold mb-1">
                    Details
                  </p>
                  <div className="space-y-0.5">
                    {permission.patterns.map((p, i) => (
                      <p key={i} className="text-xs text-[var(--text-secondary)]">
                        {p}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {!expired && (
                <>
                  <div className="flex items-center gap-2 py-2 border-t border-[var(--border-default)]">
                    <Switch
                      checked={rememberChoice}
                      onCheckedChange={setRememberChoice}
                      id="remember-choice"
                    />
                    <label
                      htmlFor="remember-choice"
                      className="text-xs text-[var(--text-secondary)] cursor-pointer select-none"
                    >
                      Remember this choice for <span className="font-medium text-[var(--text-primary)]">{displayTool}</span>
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void handleRespond(false)}
                      disabled={submitting}
                      className="gap-1.5 flex-1"
                    >
                      <ShieldX className="h-3.5 w-3.5" />
                      Deny
                    </Button>
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={() => void handleRespond(true)}
                      disabled={submitting}
                      className="gap-1.5 flex-1"
                    >
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Allow
                    </Button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
