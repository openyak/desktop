"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { HexColorPicker } from "react-colorful";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  useAppearanceStore,
  APPEARANCE_DEFAULTS,
  type ThemeKey,
  type ColorKind,
} from "@/stores/appearance-store";

export function AppearanceCustomize() {
  const { t } = useTranslation("settings");
  const reset = useAppearanceStore((s) => s.reset);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-ui-title-sm font-semibold text-[var(--text-primary)]">
          {t("customize")}
        </h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-ui-caption text-[var(--text-tertiary)]"
          onClick={reset}
        >
          {t("resetAppearance")}
        </Button>
      </div>

      <ThemeBlock theme="light" />
      <ThemeBlock theme="dark" />

      <FontBlock />

      <Separator />

      <ToggleRow
        title={t("usePointerCursors")}
        desc={t("usePointerCursorsDesc")}
        check="pointerCursors"
      />

      <NumberRow
        title={t("uiFontSize")}
        desc={t("uiFontSizeDesc")}
        field="uiFontSize"
      />
      <NumberRow
        title={t("codeFontSize")}
        desc={t("codeFontSizeDesc")}
        field="codeFontSize"
      />
    </div>
  );
}

function ThemeBlock({ theme }: { theme: ThemeKey }) {
  const { t } = useTranslation("settings");
  return (
    <div className="rounded-xl border border-[var(--border-default)] overflow-hidden">
      <div className="px-3 py-2 text-ui-overline font-semibold text-[var(--text-secondary)] uppercase tracking-wide border-b border-[var(--border-subtle)]">
        {theme === "light" ? t("lightTheme") : t("darkTheme")}
      </div>
      <ColorRow theme={theme} kind="accent" label={t("accent")} />
      <ColorRow theme={theme} kind="background" label={t("background")} />
      <ColorRow theme={theme} kind="foreground" label={t("foreground")} />
    </div>
  );
}

function ColorRow({
  theme,
  kind,
  label,
}: {
  theme: ThemeKey;
  kind: ColorKind;
  label: string;
}) {
  const stored = useAppearanceStore(
    (s) => s[colorField(theme, kind)] as string | null,
  );
  const setColor = useAppearanceStore((s) => s.setColor);
  const defaultColor = APPEARANCE_DEFAULTS[theme][kind];
  const value = stored ?? defaultColor;
  const isOverridden = stored !== null;

  return (
    <div className="flex items-center justify-between px-3 py-2 border-t border-[var(--border-subtle)] first:border-t-0">
      <span className="text-ui-body text-[var(--text-primary)]">{label}</span>
      <div className="flex items-center gap-2">
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              aria-label={label}
              className="flex items-center gap-2 rounded-full border border-[var(--border-default)] pl-1 pr-3 py-1 hover:bg-[var(--surface-secondary)] data-[state=open]:bg-[var(--surface-secondary)] transition-colors"
            >
              <span
                className="h-4 w-4 rounded-full border border-[var(--border-default)]"
                style={{ backgroundColor: value }}
              />
              <span className="text-ui-caption font-mono text-[var(--text-secondary)]">
                {value.toUpperCase()}
              </span>
            </button>
          </PopoverTrigger>
          <PopoverContent
            side="left"
            align="start"
            sideOffset={8}
            className="w-[232px] p-3 space-y-2"
          >
            <ColorPickerBody
              value={value}
              onChange={(next) => setColor(theme, kind, next)}
            />
          </PopoverContent>
        </Popover>
        {isOverridden && (
          <button
            type="button"
            onClick={() => setColor(theme, kind, null)}
            className="text-ui-3xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
          >
            reset
          </button>
        )}
      </div>
    </div>
  );
}

function ColorPickerBody({
  value,
  onChange,
}: {
  value: string;
  onChange: (hex: string) => void;
}) {
  const [draft, setDraft] = useState(value);

  // Accept either #RGB or #RRGGBB, uppercase output. Only commit when valid.
  const handleHexInput = (raw: string) => {
    setDraft(raw);
    const trimmed = raw.trim();
    const normalized = trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
    if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(normalized)) {
      onChange(normalized);
    }
  };

  return (
    <>
      <HexColorPicker
        color={value}
        onChange={(c) => {
          onChange(c);
          setDraft(c);
        }}
        style={{ width: "100%", height: 160 }}
      />
      <div className="flex items-center gap-2">
        <span
          className="h-5 w-5 rounded-md border border-[var(--border-default)] shrink-0"
          style={{ backgroundColor: value }}
        />
        <Input
          value={(draft || value).toUpperCase()}
          onChange={(e) => handleHexInput(e.target.value)}
          onBlur={() => setDraft(value)}
          spellCheck={false}
          className="h-8 text-ui-caption font-mono tracking-wider"
        />
      </div>
    </>
  );
}

function FontBlock() {
  const { t } = useTranslation("settings");
  const uiFont = useAppearanceStore((s) => s.uiFont);
  const codeFont = useAppearanceStore((s) => s.codeFont);
  const setUiFont = useAppearanceStore((s) => s.setUiFont);
  const setCodeFont = useAppearanceStore((s) => s.setCodeFont);

  return (
    <div className="rounded-xl border border-[var(--border-default)] overflow-hidden">
      <div className="flex items-center gap-3 px-3 py-2 border-b border-[var(--border-subtle)]">
        <span className="w-28 shrink-0 text-ui-body text-[var(--text-primary)]">
          {t("uiFont")}
        </span>
        <Input
          value={uiFont}
          onChange={(e) => setUiFont(e.target.value)}
          placeholder="-apple-system, Inter, sans-serif"
          className="h-8 text-ui-caption font-mono"
        />
      </div>
      <div className="flex items-center gap-3 px-3 py-2">
        <span className="w-28 shrink-0 text-ui-body text-[var(--text-primary)]">
          {t("codeFont")}
        </span>
        <Input
          value={codeFont}
          onChange={(e) => setCodeFont(e.target.value)}
          placeholder='ui-monospace, "SF Mono", Menlo'
          className="h-8 text-ui-caption font-mono"
        />
      </div>
    </div>
  );
}

function ToggleRow({
  title,
  desc,
  check,
}: {
  title: string;
  desc: string;
  check: "pointerCursors";
}) {
  const value = useAppearanceStore((s) => s[check]);
  const setter = useAppearanceStore((s) => s.setPointerCursors);
  return (
    <div className="flex items-center justify-between">
      <div className="min-w-0 pr-4">
        <p className="text-ui-body text-[var(--text-primary)]">{title}</p>
        <p className="text-ui-caption text-[var(--text-tertiary)]">{desc}</p>
      </div>
      <Switch checked={value} onCheckedChange={setter} />
    </div>
  );
}

function NumberRow({
  title,
  desc,
  field,
}: {
  title: string;
  desc: string;
  field: "uiFontSize" | "codeFontSize";
}) {
  const value = useAppearanceStore((s) => s[field]);
  const setUi = useAppearanceStore((s) => s.setUiFontSize);
  const setCode = useAppearanceStore((s) => s.setCodeFontSize);
  const setter = field === "uiFontSize" ? setUi : setCode;
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const commit = () => {
    const next = Number(draft);
    setter(Number.isFinite(next) ? next : value);
  };

  return (
    <div className="flex items-center justify-between">
      <div className="min-w-0 pr-4">
        <p className="text-ui-body text-[var(--text-primary)]">{title}</p>
        <p className="text-ui-caption text-[var(--text-tertiary)]">{desc}</p>
      </div>
      <div className="flex items-center gap-1.5">
        <Input
          type="number"
          min={10}
          max={22}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.currentTarget.blur();
            } else if (e.key === "Escape") {
              setDraft(String(value));
              e.currentTarget.blur();
            }
          }}
          className="h-8 w-16 text-ui-caption text-right"
        />
        <span className="text-ui-caption text-[var(--text-tertiary)]">px</span>
      </div>
    </div>
  );
}

function colorField(theme: ThemeKey, kind: ColorKind) {
  return `${theme}${kind[0].toUpperCase()}${kind.slice(1)}` as
    | "lightAccent"
    | "lightBackground"
    | "lightForeground"
    | "darkAccent"
    | "darkBackground"
    | "darkForeground";
}
