"use client";

import { Search } from "lucide-react";
import { useTranslation } from 'react-i18next';
import { useSidebarStore } from "@/stores/sidebar-store";

export function SidebarSearch() {
  const { t } = useTranslation('common');
  const { searchQuery, setSearchQuery } = useSidebarStore();

  return (
    <div className="px-3 py-2">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
        <input
          type="search"
          name="sidebar-search"
          placeholder={t('searchConversations')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          autoComplete="one-time-code"
          data-form-type="other"
          className="w-full rounded-lg bg-[var(--surface-secondary)] py-2 pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:ring-1 focus:ring-[var(--ring)] transition-shadow"
        />
      </div>
    </div>
  );
}
