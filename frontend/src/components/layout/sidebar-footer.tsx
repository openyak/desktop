"use client";

import { Sun, Moon, User, CreditCard } from "lucide-react";
import { useTheme } from "next-themes";
import { useTranslation } from 'react-i18next';
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { OpenYakLogo } from "@/components/ui/openyak-logo";
import { useAuthStore } from "@/stores/auth-store";

function formatTokenCompact(count: number): string {
  if (count >= 1_000_000) {
    const value = count / 1_000_000;
    const rounded = value.toFixed(1);
    return `${rounded.endsWith(".0") ? rounded.slice(0, -2) : rounded}M`;
  }
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`;
  return count.toString();
}

function AccountBadge() {
  const { t } = useTranslation('common');
  const { isConnected, user } = useAuthStore();
  if (!isConnected || !user) return null;

  if (user.billing_mode === "credits") {
    return (
      <Link
        href="/billing"
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs hover:bg-[var(--surface-secondary)] transition-colors"
      >
        <CreditCard className="h-3 w-3 text-[var(--brand-primary)]" />
        <span className="text-[var(--text-secondary)] font-mono">
          {user.credit_balance} cr
        </span>
      </Link>
    );
  }

  // Free mode — show quota bar
  const percent = Math.min(100, (user.daily_free_tokens_used / user.daily_free_token_limit) * 100);
  const usedCompact = formatTokenCompact(user.daily_free_tokens_used);
  const limitCompact = formatTokenCompact(user.daily_free_token_limit);

  return (
    <Link
      href="/billing"
      className="block px-3 py-1.5 hover:bg-[var(--surface-secondary)] transition-colors"
    >
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <OpenYakLogo size={12} className="text-[var(--brand-primary)]" />
            <span className="text-[10px] text-[var(--text-tertiary)]">{t('free')}</span>
          </div>
          <span className="text-[10px] text-[var(--text-tertiary)] font-mono">
            {usedCompact} / {limitCompact}
          </span>
        </div>
      <div className="w-full bg-[var(--surface-tertiary)] rounded-full h-1">
        <div
          className="h-1 rounded-full transition-all"
          style={{
            width: `${percent}%`,
            backgroundColor:
              percent >= 90
                ? "var(--color-destructive)"
                : percent >= 70
                  ? "var(--color-warning)"
                  : "var(--brand-primary)",
          }}
        />
      </div>
    </Link>
  );
}

export function SidebarFooter() {
  const { t } = useTranslation('common');
  const { theme, setTheme } = useTheme();
  const { isConnected, user } = useAuthStore();

  const displayName = isConnected && user ? user.email.split("@")[0] : t('localUser');

  return (
    <div className="border-t border-[var(--border-default)]">
      <AccountBadge />
      <div className="flex items-center gap-3 px-3 py-3.5">
        {/* User avatar */}
        <div className="h-9 w-9 rounded-full bg-[var(--surface-tertiary)] flex items-center justify-center shrink-0">
          <User className="h-[18px] w-[18px] text-[var(--text-secondary)]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)] truncate">{displayName}</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={t('toggleTheme')}
        >
          <Sun className="h-[18px] w-[18px] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[18px] w-[18px] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
      </div>
    </div>
  );
}
