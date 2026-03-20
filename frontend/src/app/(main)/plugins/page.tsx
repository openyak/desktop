"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  Plus,
  Plug,
  RotateCw,
  Sparkles,
  Unplug,
  Workflow,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { API, IS_DESKTOP, queryKeys } from "@/lib/constants";
import { desktopAPI } from "@/lib/tauri-api";
import {
  usePluginsStatus,
  usePluginDetail,
  usePluginToggle,
  useSkills,
} from "@/hooks/use-plugins";
import {
  useConnectors,
  useConnectorToggle,
  useConnectorConnect,
  useConnectorDisconnect,
  useConnectorReconnect,
  useAddCustomConnector,
  useSetConnectorToken,
} from "@/hooks/use-connectors";
import type { PluginInfo, SkillInfo } from "@/types/plugins";
import type { ConnectorInfo } from "@/types/connectors";

const SOURCE_COLORS: Record<string, string> = {
  builtin: "bg-blue-500/10 text-blue-400",
  global: "bg-amber-500/10 text-amber-400",
  project: "bg-emerald-500/10 text-emerald-400",
  plugin: "bg-purple-500/10 text-purple-400",
  bundled: "bg-blue-500/10 text-blue-400",
  custom: "bg-orange-500/10 text-orange-400",
};

const CATEGORY_LABELS: Record<string, string> = {
  communication: "Communication",
  productivity: "Productivity",
  "dev-tools": "Developer Tools",
  design: "Design",
  crm: "CRM",
  analytics: "Analytics",
  marketing: "Marketing",
  sales: "Sales",
  data: "Data",
  legal: "Legal",
  operations: "Operations",
  knowledge: "Knowledge",
  "bio-research": "Bio Research",
  custom: "Custom",
  other: "Other",
};

type Tab = "connectors" | "plugins" | "skills";

export default function PluginsPage() {
  const { t } = useTranslation("plugins");
  const [tab, setTab] = useState<Tab>("connectors");
  const [search, setSearch] = useState("");

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 lg:hidden"
            asChild
          >
            <Link href="/c/new">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <Plug className="h-5 w-5 text-[var(--text-secondary)]" />
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">
            {t("title")}
          </h1>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-4 border-b border-[var(--border-default)]">
          {(["connectors", "plugins", "skills"] as Tab[]).map((tabKey) => (
            <button
              key={tabKey}
              onClick={() => { setTab(tabKey); setSearch(""); }}
              className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 -mb-px ${
                tab === tabKey
                  ? "border-[var(--text-primary)] text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
              }`}
            >
              {tabKey === "connectors"
                ? t("connectorsTab")
                : tabKey === "plugins"
                  ? t("pluginsTab")
                  : t("skills")}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full h-8 rounded-md border border-[var(--border-default)] bg-transparent px-3 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
          />
        </div>

        {/* Content */}
        {tab === "connectors" ? (
          <ConnectorsTab search={search} />
        ) : tab === "plugins" ? (
          <PluginsTab search={search} />
        ) : (
          <SkillsTab search={search} />
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Connectors Tab                                                      */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, string> = {
  connected: "bg-emerald-500",
  needs_auth: "bg-amber-500",
  failed: "bg-red-500",
  disconnected: "bg-[var(--text-tertiary)]",
  disabled: "bg-[var(--text-tertiary)]",
};

function ConnectorsTab({ search }: { search: string }) {
  const { t } = useTranslation("plugins");
  const { data, isLoading } = useConnectors();
  const [showAdd, setShowAdd] = useState(false);

  const connectors = data?.connectors ?? {};
  const entries = Object.entries(connectors);
  const connectedCount = entries.filter(([, c]) => c.status === "connected").length;

  const filtered = search
    ? entries.filter(
        ([id, c]) =>
          id.toLowerCase().includes(search.toLowerCase()) ||
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          c.description.toLowerCase().includes(search.toLowerCase()),
      )
    : entries;

  // Group by category
  const byCategory: Record<string, [string, ConnectorInfo][]> = {};
  for (const entry of filtered) {
    const cat = entry[1].category || "other";
    (byCategory[cat] ??= []).push(entry);
  }

  // Sort categories
  const categoryOrder = [
    "communication", "productivity", "dev-tools", "design", "crm",
    "analytics", "marketing", "sales", "data", "legal", "operations",
    "knowledge", "bio-research", "custom", "other",
  ];
  const sortedCategories = Object.keys(byCategory).sort(
    (a, b) => (categoryOrder.indexOf(a) ?? 99) - (categoryOrder.indexOf(b) ?? 99),
  );

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        {!isLoading && (
          <p className="text-[11px] text-[var(--text-tertiary)]">
            {t("connectedCount", { count: connectedCount })} / {entries.length}
          </p>
        )}
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-[11px] px-2.5"
          onClick={() => setShowAdd(!showAdd)}
        >
          <Plus className="h-3 w-3 mr-1" />
          {t("addCustom")}
        </Button>
      </div>

      {showAdd && <AddConnectorForm onClose={() => setShowAdd(false)} />}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-14 rounded-lg bg-[var(--surface-tertiary)] animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-xs text-[var(--text-tertiary)] text-center py-8">
          {t("noConnectors")}
        </p>
      ) : (
        <div className="space-y-5">
          {sortedCategories.map((cat) => (
            <div key={cat}>
              <h3 className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">
                {CATEGORY_LABELS[cat] ?? cat} ({byCategory[cat].length})
              </h3>
              <div className="space-y-1.5">
                {byCategory[cat].map(([id, connector]) => (
                  <ConnectorRow key={id} id={id} connector={connector} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function ConnectorRow({
  id,
  connector,
}: {
  id: string;
  connector: ConnectorInfo;
}) {
  const { t } = useTranslation("plugins");
  const toggle = useConnectorToggle();
  const connect = useConnectorConnect();
  const disconnect = useConnectorDisconnect();
  const reconnect = useConnectorReconnect();
  const setToken = useSetConnectorToken();
  const [tokenInput, setTokenInput] = useState("");

  const isPending =
    toggle.isPending || connect.isPending || disconnect.isPending || reconnect.isPending;

  const qc = useQueryClient();

  const handleConnect = async () => {
    // Google Workspace uses direct Google OAuth (not MCP OAuth)
    const isGoogle = id === "google-workspace";
    const result = isGoogle
      ? await api.post<{ success: boolean; auth_url?: string; state?: string; error?: string }>(API.GOOGLE.AUTH_START)
      : await connect.mutateAsync(id);

    if (result.success && result.auth_url) {
      if (IS_DESKTOP) {
        // Tauri: open system browser + poll for auth completion
        await desktopAPI.openExternal(result.auth_url);
        const poll = setInterval(async () => {
          await qc.invalidateQueries({ queryKey: queryKeys.connectors });
        }, 3000);
        // Stop polling after 5 minutes
        setTimeout(() => clearInterval(poll), 300_000);
      } else {
        // Web: open popup + listen for postMessage
        const popup = window.open(
          result.auth_url,
          "connector-auth",
          "width=600,height=700,menubar=no,toolbar=no",
        );
        const handler = (event: MessageEvent) => {
          if (
            event.data?.type === "connector-auth-complete" ||
            event.data?.type === "mcp-auth-complete"
          ) {
            window.removeEventListener("message", handler);
            qc.invalidateQueries({ queryKey: queryKeys.connectors });
          }
        };
        window.addEventListener("message", handler);
        if (popup) {
          const timer = setInterval(() => {
            if (popup.closed) {
              clearInterval(timer);
              window.removeEventListener("message", handler);
              // Also refresh in case auth completed before popup closed
              qc.invalidateQueries({ queryKey: queryKeys.connectors });
            }
          }, 1000);
        }
      }
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-2.5">
      {/* Status dot */}
      <span
        className={`h-2 w-2 rounded-full shrink-0 ${
          STATUS_COLORS[connector.status] ?? STATUS_COLORS.disconnected
        }`}
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-[var(--text-primary)]">
            {connector.name}
          </span>
          {connector.type === "local" && id !== "google-workspace" && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400">
              {t("localSetup")}
            </span>
          )}
          {connector.source === "custom" && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${SOURCE_COLORS.custom}`}>
              {t("custom")}
            </span>
          )}
          {connector.status === "connected" && connector.tools_count > 0 && (
            <span className="text-[10px] text-[var(--text-tertiary)]">
              {connector.tools_count} {t("tools")}
            </span>
          )}
        </div>
        <p className="text-[10px] text-[var(--text-tertiary)] truncate mt-0.5">
          {connector.description}
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 shrink-0">
        {connector.status === "needs_auth" && (
          <Button
            variant="outline"
            size="sm"
            className="h-6 text-[10px] px-2"
            onClick={handleConnect}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <ExternalLink className="h-3 w-3" />
            )}
            <span className="ml-1">{t("connect")}</span>
          </Button>
        )}

        {(connector.status === "needs_auth" || connector.status === "failed") && connector.enabled && (
          <form
            className="flex items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              if (tokenInput.trim()) {
                setToken.mutate({ id, token: tokenInput.trim() });
                setTokenInput("");
              }
            }}
          >
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Token / PAT"
              className="h-6 w-28 rounded border border-[var(--border-default)] bg-transparent px-1.5 text-[10px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
            />
            <Button
              type="submit"
              variant="outline"
              size="sm"
              className="h-6 text-[10px] px-2"
              disabled={!tokenInput.trim() || setToken.isPending}
            >
              {setToken.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "OK"}
            </Button>
          </form>
        )}

        {connector.status === "connected" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] px-1.5 text-[var(--text-tertiary)]"
            onClick={() => disconnect.mutate(id)}
            disabled={isPending}
            title={t("disconnect")}
          >
            <Unplug className="h-3 w-3" />
          </Button>
        )}

        {connector.status === "failed" && (
          <Button
            variant="outline"
            size="sm"
            className="h-6 text-[10px] px-2"
            onClick={() => reconnect.mutate(id)}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RotateCw className="h-3 w-3" />
            )}
            <span className="ml-1">{t("retry")}</span>
          </Button>
        )}

        {/* Enable/disable toggle */}
        <Switch
          checked={connector.enabled}
          onCheckedChange={async (checked) => {
            await toggle.mutateAsync({ id, enable: checked });
            if (checked && (connector.type === "remote" || id === "google-workspace")) {
              // Remote or Google: auto-trigger OAuth after enable
              await new Promise((r) => setTimeout(r, 500));
              await qc.invalidateQueries({ queryKey: queryKeys.connectors });
              handleConnect();
            } else if (checked) {
              // Local: just refresh status
              await new Promise((r) => setTimeout(r, 1000));
              await qc.invalidateQueries({ queryKey: queryKeys.connectors });
            }
          }}
          disabled={toggle.isPending}
          className="shrink-0"
        />
      </div>
    </div>
  );
}

function AddConnectorForm({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("plugins");
  const addConnector = useAddCustomConnector();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !url) return;
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    await addConnector.mutateAsync({ id, name, url });
    onClose();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-4 rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] p-3 space-y-2.5"
    >
      <h4 className="text-xs font-semibold text-[var(--text-primary)]">
        {t("addConnector")}
      </h4>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={t("connectorName")}
        className="w-full h-7 rounded-md border border-[var(--border-default)] bg-transparent px-2.5 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
        required
      />
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://mcp.example.com/mcp"
        className="w-full h-7 rounded-md border border-[var(--border-default)] bg-transparent px-2.5 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
        required
      />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" className="h-7 text-[11px]" onClick={onClose} type="button">
          {t("cancel")}
        </Button>
        <Button size="sm" className="h-7 text-[11px]" type="submit" disabled={addConnector.isPending}>
          {addConnector.isPending ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          {t("add")}
        </Button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/* Plugins Tab                                                         */
/* ------------------------------------------------------------------ */

function PluginsTab({ search }: { search: string }) {
  const { t } = useTranslation("plugins");
  const { data, isLoading } = usePluginsStatus();
  const [expanded, setExpanded] = useState<string | null>(null);

  const plugins = data?.plugins ?? {};
  const entries = Object.entries(plugins);
  const enabledCount = entries.filter(([, p]) => p.enabled).length;

  const filtered = search
    ? entries.filter(
        ([name, p]) =>
          name.toLowerCase().includes(search.toLowerCase()) ||
          p.description.toLowerCase().includes(search.toLowerCase()),
      )
    : entries;

  return (
    <>
      {!isLoading && (
        <p className="text-[11px] text-[var(--text-tertiary)] mb-3">
          {t("enabledCount", { count: enabledCount })} / {entries.length}
        </p>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-lg bg-[var(--surface-tertiary)] animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-xs text-[var(--text-tertiary)] text-center py-8">
          {t("noPlugins")}
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map(([name, plugin]) => (
            <PluginCard
              key={name}
              name={name}
              plugin={plugin}
              expanded={expanded === name}
              onToggleExpand={() =>
                setExpanded(expanded === name ? null : name)
              }
            />
          ))}
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Skills Tab                                                          */
/* ------------------------------------------------------------------ */

function SkillsTab({ search }: { search: string }) {
  const { t } = useTranslation("plugins");
  const { data: skills, isLoading } = useSkills();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-10 rounded-lg bg-[var(--surface-tertiary)] animate-pulse"
          />
        ))}
      </div>
    );
  }

  const allSkills = skills ?? [];

  const bundled = allSkills.filter((s) => s.source === "bundled");
  const plugin = allSkills.filter((s) => s.source === "plugin");
  const project = allSkills.filter((s) => s.source === "project");

  const filterSkills = (list: SkillInfo[]) =>
    search
      ? list.filter(
          (s) =>
            s.name.toLowerCase().includes(search.toLowerCase()) ||
            s.description.toLowerCase().includes(search.toLowerCase()),
        )
      : list;

  const filteredBundled = filterSkills(bundled);
  const filteredPlugin = filterSkills(plugin);
  const filteredProject = filterSkills(project);

  const total = filteredBundled.length + filteredPlugin.length + filteredProject.length;

  if (total === 0) {
    return (
      <p className="text-xs text-[var(--text-tertiary)] text-center py-8">
        {t("noSkills")}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {filteredBundled.length > 0 && (
        <SkillGroup
          title={t("bundledSkills")}
          skills={filteredBundled}
          source="bundled"
        />
      )}
      {filteredPlugin.length > 0 && (
        <SkillGroup
          title={t("pluginSkills")}
          skills={filteredPlugin}
          source="plugin"
        />
      )}
      {filteredProject.length > 0 && (
        <SkillGroup
          title={t("projectSkills")}
          skills={filteredProject}
          source="project"
        />
      )}
    </div>
  );
}

function SkillGroup({
  title,
  skills,
  source,
}: {
  title: string;
  skills: SkillInfo[];
  source: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-xs font-semibold text-[var(--text-secondary)]">
          {title}
        </h3>
        <span className="text-[10px] text-[var(--text-tertiary)]">
          ({skills.length})
        </span>
      </div>
      <div className="space-y-1">
        {skills.map((skill) => (
          <div
            key={skill.name}
            className="flex items-start gap-3 rounded-lg border border-[var(--border-default)] p-2.5"
          >
            <Sparkles className="h-3.5 w-3.5 text-[var(--text-tertiary)] mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-medium text-[var(--text-primary)]">
                  {skill.name}
                </span>
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                    SOURCE_COLORS[source] ?? SOURCE_COLORS.bundled
                  }`}
                >
                  {skill.name.includes(":") ? skill.name.split(":")[0] : source}
                </span>
              </div>
              <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5 line-clamp-2">
                {skill.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Plugin Card + Detail                                                */
/* ------------------------------------------------------------------ */

function PluginCard({
  name,
  plugin,
  expanded,
  onToggleExpand,
}: {
  name: string;
  plugin: PluginInfo;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const { t } = useTranslation("plugins");
  const toggle = usePluginToggle();

  return (
    <div className="rounded-lg border border-[var(--border-default)] overflow-hidden">
      {/* Main row */}
      <div className="flex items-center gap-3 p-3">
        <button
          onClick={onToggleExpand}
          className="shrink-0 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>

        <span
          className={`h-2 w-2 rounded-full shrink-0 ${
            plugin.enabled ? "bg-emerald-500" : "bg-[var(--text-tertiary)]"
          }`}
        />

        <div className="flex-1 min-w-0" onClick={onToggleExpand} role="button">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-[var(--text-primary)] truncate">
              {name}
            </p>
            <span className="text-[10px] text-[var(--text-tertiary)]">
              {t("version", { version: plugin.version })}
            </span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                SOURCE_COLORS[plugin.source] ?? SOURCE_COLORS.builtin
              }`}
            >
              {t(plugin.source)}
            </span>
          </div>
          <p className="text-[11px] text-[var(--text-tertiary)] truncate mt-0.5">
            {plugin.description}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 text-[11px] text-[var(--text-tertiary)]">
          <span className="flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            {plugin.skills_count}
          </span>
          {plugin.mcp_count > 0 && (
            <span className="flex items-center gap-1">
              <Workflow className="h-3 w-3" />
              {plugin.mcp_count}
            </span>
          )}
        </div>

        <Switch
          checked={plugin.enabled}
          onCheckedChange={(checked) =>
            toggle.mutate({ name, enable: checked })
          }
          disabled={toggle.isPending}
          className="shrink-0"
        />
      </div>

      {expanded && <PluginDetailPanel name={name} />}
    </div>
  );
}

function PluginDetailPanel({ name }: { name: string }) {
  const { t } = useTranslation("plugins");
  const { data, isLoading } = usePluginDetail(name);
  const { data: connectorsData } = useConnectors();

  const connectors = connectorsData?.connectors ?? {};

  if (isLoading) {
    return (
      <div className="border-t border-[var(--border-default)] p-3">
        <div className="h-8 rounded bg-[var(--surface-tertiary)] animate-pulse" />
      </div>
    );
  }

  if (!data) return null;

  const connectorIds = data.connector_ids ?? [];

  return (
    <div className="border-t border-[var(--border-default)] bg-[var(--surface-secondary)] px-3 py-3">
      {/* Skills */}
      {data.skills.length > 0 && (
        <div className="mb-3">
          <h4 className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
            {t("skills")} ({data.skills.length})
          </h4>
          <div className="space-y-1">
            {data.skills.map((skill) => (
              <div key={skill.name} className="flex gap-2">
                <span className="text-xs font-mono text-[var(--text-primary)] shrink-0">
                  {skill.name}
                </span>
                <span className="text-[11px] text-[var(--text-tertiary)] truncate">
                  {skill.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Required connectors */}
      {connectorIds.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
            {t("requiredConnectors")} ({connectorIds.length})
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {connectorIds.map((cid) => {
              const connector = connectors[cid];
              const statusColor = connector
                ? STATUS_COLORS[connector.status] ?? STATUS_COLORS.disconnected
                : STATUS_COLORS.disconnected;

              return (
                <span
                  key={cid}
                  className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-primary)] rounded border border-[var(--border-default)] bg-[var(--surface-primary)] px-2 py-1"
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${statusColor}`} />
                  {connector?.name ?? cid}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
