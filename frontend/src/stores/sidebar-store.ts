"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type OrganizeMode = "by-project" | "chronological" | "chats-first";
export type SortBy = "created" | "updated";

interface SidebarStore {
  /** Mobile drawer open state */
  isOpen: boolean;
  /** Desktop sidebar collapsed state */
  isCollapsed: boolean;
  /** Whether the search input is visible */
  isSearchOpen: boolean;
  searchQuery: string;
  /** Project directories that user has collapsed (default: expanded) */
  collapsedProjects: Record<string, boolean>;
  /** Command-palette search dialog open state */
  isSearchModalOpen: boolean;
  /** How session list is organized */
  organizeMode: OrganizeMode;
  /** Which timestamp sessions are sorted by */
  sortBy: SortBy;
  setOpen: (open: boolean) => void;
  /** Toggle desktop sidebar collapse */
  toggle: () => void;
  toggleSearch: () => void;
  setSearchQuery: (query: string) => void;
  toggleProjectCollapsed: (directory: string) => void;
  setSearchModalOpen: (open: boolean) => void;
  setOrganizeMode: (mode: OrganizeMode) => void;
  setSortBy: (sortBy: SortBy) => void;
  collapseAllProjects: (directories: string[]) => void;
  expandAllProjects: () => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set) => ({
      isOpen: false,
      isCollapsed: false,
      isSearchOpen: false,
      searchQuery: "",
      collapsedProjects: {},
      isSearchModalOpen: false,
      organizeMode: "by-project",
      sortBy: "updated",
      setOpen: (open) => set({ isOpen: open }),
      toggle: () => set((s) => ({ isCollapsed: !s.isCollapsed })),
      toggleSearch: () =>
        set((s) => ({
          isSearchOpen: !s.isSearchOpen,
          searchQuery: s.isSearchOpen ? "" : s.searchQuery,
        })),
      setSearchQuery: (query) => set({ searchQuery: query }),
      toggleProjectCollapsed: (directory) =>
        set((s) => {
          const next = { ...s.collapsedProjects };
          if (next[directory]) delete next[directory];
          else next[directory] = true;
          return { collapsedProjects: next };
        }),
      setSearchModalOpen: (open) => set({ isSearchModalOpen: open }),
      setOrganizeMode: (mode) => set({ organizeMode: mode }),
      setSortBy: (sortBy) => set({ sortBy }),
      collapseAllProjects: (directories) =>
        set(() => {
          const next: Record<string, boolean> = {};
          for (const d of directories) next[d] = true;
          return { collapsedProjects: next };
        }),
      expandAllProjects: () => set({ collapsedProjects: {} }),
    }),
    {
      name: "openyak-sidebar",
      partialize: (s) => ({
        collapsedProjects: s.collapsedProjects,
        organizeMode: s.organizeMode,
        sortBy: s.sortBy,
      }),
    },
  ),
);
