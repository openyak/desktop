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
    <div className="flex h-14 items-center justify-between px-3">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="h-9 w-9" onClick={toggle}>
            <PanelLeft className="h-[18px] w-[18px]" />
            <span className="sr-only">{t('toggleSidebar')}</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">{t('toggleSidebar')}</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="h-9 w-9" asChild>
            <Link href="/c/new">
              <SquarePen className="h-[18px] w-[18px]" />
              <span className="sr-only">{t('newChat')}</span>
            </Link>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">{t('newChat')}</TooltipContent>
      </Tooltip>
    </div>
  );
}
