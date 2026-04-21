"use client";

import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSidebarStore } from "@/stores/sidebar-store";

export function SidebarNav() {
  const { t } = useTranslation("common");
  const setSearchModalOpen = useSidebarStore((s) => s.setSearchModalOpen);

  return (
    <nav className="flex flex-col px-3 pt-1 pb-1">
      <button
        type="button"
        onClick={() => setSearchModalOpen(true)}
        className="flex items-center gap-2 rounded-lg px-2 py-1 text-[13px] text-[var(--text-secondary)] transition-colors hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)]"
      >
        <Search className="h-[13px] w-[13px] shrink-0" />
        <span className="flex-1 text-left">{t("searchChats")}</span>
      </button>
    </nav>
  );
}
