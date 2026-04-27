import SettingsPageClient from "@/components/settings/settings-layout";
import { SETTINGS_TABS, type SettingsTabId } from "@/components/settings/settings-tabs";

interface SettingsPageProps {
  searchParams?: Promise<{ tab?: string | string[] }>;
}

const SETTINGS_TAB_IDS = new Set<string>(SETTINGS_TABS.map((tab) => tab.id));

function toSettingsTabId(value: string | undefined): SettingsTabId {
  return SETTINGS_TAB_IDS.has(value ?? "") ? (value as SettingsTabId) : "general";
}

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const params = await searchParams;
  const rawTab = Array.isArray(params?.tab) ? params.tab[0] : params?.tab;
  return <SettingsPageClient initialTab={toSettingsTabId(rawTab)} />;
}
