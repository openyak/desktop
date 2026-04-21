"use client";

import Link from "next/link";
import { useTranslation } from 'react-i18next';
import { PanelLeft, SquarePen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useSidebarStore } from "@/stores/sidebar-store";

export function SidebarHeader() {
  const { t } = useTranslation('common');
  const toggle = useSidebarStore((s) => s.toggle);

  return (
    <div className="flex h-14 items-center justify-between px-4 pt-1">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)]"
            onClick={toggle}
          >
            <PanelLeft className="h-[17px] w-[17px]" />
            <span className="sr-only">{t('toggleSidebar')}</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">{t('toggleSidebar')}</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)]"
            asChild
          >
            <Link href="/c/new">
              <SquarePen className="h-[17px] w-[17px]" />
              <span className="sr-only">{t('newChat')}</span>
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">{t('newChat')}</TooltipContent>
      </Tooltip>
    </div>
  );
}
