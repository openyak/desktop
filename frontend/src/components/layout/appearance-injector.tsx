"use client";

import { useEffect } from "react";
import { useAppearanceStore } from "@/stores/appearance-store";

const STYLE_ID = "openyak-appearance-overrides";

/**
 * Writes appearance overrides into a single <style> element in <head>.
 *
 * Mutates the element's textContent directly from a zustand `.subscribe`
 * callback instead of going through React's renderer — React treats
 * <style> children specially in places (hoisting, deduping, precedence)
 * and can drop updates. Direct DOM writes are bulletproof and cheap.
 */
export function AppearanceInjector() {
  useEffect(() => {
    let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
    if (!el) {
      el = document.createElement("style");
      el.id = STYLE_ID;
      document.head.appendChild(el);
    }

    const apply = () => {
      el!.textContent = buildCss(useAppearanceStore.getState());
    };
    apply();

    return useAppearanceStore.subscribe(apply);
  }, []);

  return null;
}

function buildCss(
  s: ReturnType<typeof useAppearanceStore.getState>,
): string {
  const rules: string[] = [];

  const lightDecls = buildThemeDecls({
    accent: s.lightAccent,
    background: s.lightBackground,
    foreground: s.lightForeground,
  });
  if (lightDecls.length) {
    rules.push(`:root:not(.dark) { ${lightDecls.join(" ")} }`);
  }

  const darkDecls = buildThemeDecls({
    accent: s.darkAccent,
    background: s.darkBackground,
    foreground: s.darkForeground,
  });
  if (darkDecls.length) {
    rules.push(`.dark { ${darkDecls.join(" ")} }`);
  }

  const uiFont = sanitizeFont(s.uiFont);
  if (uiFont) {
    rules.push(
      `body, button, input, textarea, select { font-family: ${uiFont}, var(--font-sans), var(--font-cjk), system-ui, -apple-system, BlinkMacSystemFont, sans-serif; }`,
    );
  }

  const codeFont = sanitizeFont(s.codeFont);
  if (codeFont) {
    rules.push(
      `code, pre, kbd, samp, .font-mono { font-family: ${codeFont}, var(--font-mono), ui-monospace, "SF Mono", Menlo, monospace !important; }`,
    );
  }

  rules.push(
    `:root { --ui-font-size-base: ${s.uiFontSize}px; --ui-code-font-size-base: ${s.codeFontSize}px; }`,
  );
  rules.push(`body { font-size: var(--ui-size-sm); }`);
  rules.push(
    `code, pre, kbd, samp, .font-mono, .text-ui-code { font-size: var(--ui-code-font-size-base) !important; }`,
  );

  if (s.pointerCursors) {
    rules.push(
      `button:not([disabled]), [role="button"]:not([aria-disabled="true"]), a[href], [role="link"], [role="tab"], [role="menuitem"] { cursor: pointer; }`,
    );
  }

  return rules.join("\n");
}

function buildThemeDecls({
  accent,
  background,
  foreground,
}: {
  accent: string | null;
  background: string | null;
  foreground: string | null;
}): string[] {
  const decls: string[] = [];
  const bg = background?.trim() || null;
  const fg = foreground?.trim() || null;
  const ac = accent?.trim() || null;

  if (ac) {
    decls.push(
      `--brand-primary: ${ac};`,
      `--ring: ${ac};`,
      `--brand-primary-hover: color-mix(in srgb, ${ac} 84%, black);`,
    );
  }

  if (bg) {
    decls.push(
      `--surface-primary: ${bg};`,
      `--surface-chat: ${bg};`,
      `--surface-secondary: color-mix(in srgb, ${bg} 94%, ${fg ?? "#808080"} 6%);`,
      `--surface-tertiary: color-mix(in srgb, ${bg} 88%, ${fg ?? "#808080"} 12%);`,
      `--sidebar-bg: color-mix(in srgb, ${bg} 92%, ${fg ?? "#808080"} 8%);`,
      // 88% alpha of the computed sidebar-bg — keeps light-theme sidebars readable
      // against any wallpaper/vibrancy behind them. .dark rule overrides for dark themes.
      `--sidebar-translucent-bg: color-mix(in srgb, color-mix(in srgb, ${bg} 92%, ${fg ?? "#808080"} 8%) 88%, transparent);`,
      `--sidebar-hover: color-mix(in srgb, ${bg} 86%, ${fg ?? "#808080"} 14%);`,
      `--sidebar-active: color-mix(in srgb, ${bg} 80%, ${fg ?? "#808080"} 20%);`,
      `--user-bubble-bg: color-mix(in srgb, ${bg} 90%, ${fg ?? "#808080"} 10%);`,
    );
  }

  if (fg) {
    decls.push(
      `--text-primary: ${fg};`,
      `--text-secondary: color-mix(in srgb, ${fg} 72%, ${bg ?? "#ffffff"} 28%);`,
      `--text-tertiary: color-mix(in srgb, ${fg} 52%, ${bg ?? "#ffffff"} 48%);`,
      `--border-default: color-mix(in srgb, ${fg} 14%, ${bg ?? "#ffffff"} 86%);`,
      `--border-heavy: color-mix(in srgb, ${fg} 22%, ${bg ?? "#ffffff"} 78%);`,
      `--border-subtle: color-mix(in srgb, ${fg} 8%, ${bg ?? "#ffffff"} 92%);`,
      `--sidebar-active-border: color-mix(in srgb, ${fg} 10%, ${bg ?? "#ffffff"} 90%);`,
      `--switch-checked: ${ac ?? fg};`,
    );
  }

  return decls;
}

function sanitizeFont(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/[{};<>]/.test(trimmed)) return "";
  if (/[,"']/.test(trimmed)) return trimmed;
  return /\s/.test(trimmed) ? `"${trimmed}"` : trimmed;
}
