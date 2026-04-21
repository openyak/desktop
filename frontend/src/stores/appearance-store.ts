"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeKey = "light" | "dark";
export type ColorKind = "accent" | "background" | "foreground";

/** Stock theme defaults — match the base tokens in globals.css. Used as
 *  placeholder values in the UI when the user hasn't overridden yet. */
export const APPEARANCE_DEFAULTS = {
  light: { accent: "#339CFF", background: "#FFFFFF", foreground: "#1A1C1F" },
  dark: { accent: "#339CFF", background: "#181818", foreground: "#FFFFFF" },
  uiFontSize: 13,
  codeFontSize: 12,
} as const;

interface AppearanceState {
  /** Hex override for light-theme brand accent, or null to use the stock token */
  lightAccent: string | null;
  lightBackground: string | null;
  lightForeground: string | null;
  darkAccent: string | null;
  darkBackground: string | null;
  darkForeground: string | null;
  /** Free-form font-family string to prepend to the UI font stack */
  uiFont: string;
  /** Free-form font-family string to prepend to the mono font stack */
  codeFont: string;
  /** Base UI font size in px */
  uiFontSize: number;
  /** Base code/mono font size in px */
  codeFontSize: number;
  /** Whether interactive elements get a pointer cursor */
  pointerCursors: boolean;

  setColor: (theme: ThemeKey, kind: ColorKind, value: string | null) => void;
  setUiFont: (v: string) => void;
  setCodeFont: (v: string) => void;
  setUiFontSize: (v: number) => void;
  setCodeFontSize: (v: number) => void;
  setPointerCursors: (v: boolean) => void;
  reset: () => void;
}

const INITIAL: Omit<
  AppearanceState,
  | "setColor"
  | "setUiFont"
  | "setCodeFont"
  | "setUiFontSize"
  | "setCodeFontSize"
  | "setPointerCursors"
  | "reset"
> = {
  lightAccent: null,
  lightBackground: null,
  lightForeground: null,
  darkAccent: null,
  darkBackground: null,
  darkForeground: null,
  uiFont: "",
  codeFont: "",
  uiFontSize: APPEARANCE_DEFAULTS.uiFontSize,
  codeFontSize: APPEARANCE_DEFAULTS.codeFontSize,
  pointerCursors: false,
};

function colorKey(theme: ThemeKey, kind: ColorKind): keyof AppearanceState {
  const Kind = kind[0].toUpperCase() + kind.slice(1);
  return `${theme}${Kind}` as keyof AppearanceState;
}

export const useAppearanceStore = create<AppearanceState>()(
  persist(
    (set) => ({
      ...INITIAL,
      setColor: (theme, kind, value) =>
        set({ [colorKey(theme, kind)]: value } as Partial<AppearanceState>),
      setUiFont: (v) => set({ uiFont: v }),
      setCodeFont: (v) => set({ codeFont: v }),
      setUiFontSize: (v) => set({ uiFontSize: clamp(v, 10, 22) }),
      setCodeFontSize: (v) => set({ codeFontSize: clamp(v, 10, 22) }),
      setPointerCursors: (v) => set({ pointerCursors: v }),
      reset: () => set(INITIAL),
    }),
    { name: "openyak-appearance" },
  ),
);

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, Number.isFinite(n) ? n : lo));
}
