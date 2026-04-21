"use client";

import { WORKSPACE_PANEL_WIDTH, IS_DESKTOP, TITLE_BAR_HEIGHT } from "@/lib/constants";
import { ProgressCard } from "./progress-section";
import { FilesCard } from "./files-section";
import { ContextCard } from "./context-section";

export function WorkspacePanel() {
  return (
    <aside
      className="fixed inset-y-0 right-0 z-30 flex flex-col overflow-hidden bg-[var(--surface-chat)]"
      style={{
        width: WORKSPACE_PANEL_WIDTH,
        ...(IS_DESKTOP ? { top: TITLE_BAR_HEIGHT } : {}),
      }}
    >
      <div className="flex-1 overflow-y-auto overscroll-contain px-3 py-4 space-y-3 scrollbar-auto">
        <ProgressCard />
        <FilesCard />
        <ContextCard />
      </div>
    </aside>
  );
}
