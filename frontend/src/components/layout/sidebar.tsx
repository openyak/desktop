"use client";

import { Suspense } from "react";
import { motion } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarHeader } from "./sidebar-header";
import { SidebarNav } from "./sidebar-nav";
import { SessionList } from "./session-list";
import { SidebarFooter } from "./sidebar-footer";
import { useSidebarStore } from "@/stores/sidebar-store";
import { SIDEBAR_WIDTH, IS_DESKTOP, TITLE_BAR_HEIGHT } from "@/lib/constants";

export function Sidebar() {
  const isCollapsed = useSidebarStore((s) => s.isCollapsed);

  return (
    <TooltipProvider delayDuration={200}>
      <motion.aside
        aria-label="Chat sidebar"
        className="fixed inset-y-0 left-0 z-30 flex flex-col bg-[var(--sidebar-bg)] overflow-hidden"
        style={IS_DESKTOP ? { top: TITLE_BAR_HEIGHT } : undefined}
        initial={false}
        animate={{ width: isCollapsed ? 0 : SIDEBAR_WIDTH }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <SidebarHeader />
        <SidebarNav />
        <Suspense fallback={<div className="flex-1" />}>
          <SessionList />
        </Suspense>
        <SidebarFooter />
      </motion.aside>
    </TooltipProvider>
  );
}
