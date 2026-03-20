"use client";

import { create } from "zustand";

interface SidebarStore {
  /** Mobile drawer open state */
  isOpen: boolean;
  /** Desktop sidebar collapsed state */
  isCollapsed: boolean;
  /** Whether the search input is visible */
  isSearchOpen: boolean;
  searchQuery: string;
  setOpen: (open: boolean) => void;
  /** Toggle desktop sidebar collapse */
  toggle: () => void;
  toggleSearch: () => void;
  setSearchQuery: (query: string) => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  isOpen: false,
  isCollapsed: false,
  isSearchOpen: false,
  searchQuery: "",
  setOpen: (open) => set({ isOpen: open }),
  toggle: () => set((s) => ({ isCollapsed: !s.isCollapsed })),
  toggleSearch: () =>
    set((s) => ({
      isSearchOpen: !s.isSearchOpen,
      searchQuery: s.isSearchOpen ? "" : s.searchQuery,
    })),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
