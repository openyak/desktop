/** Plugin management types */

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  author: string;
  enabled: boolean;
  source: "builtin" | "global" | "project";
  skills_count: number;
  mcp_count: number;
}

export interface PluginDetail extends PluginInfo {
  skills: Array<{ name: string; description: string }>;
  connector_ids: string[];
}

export interface PluginsStatusResponse {
  plugins: Record<string, PluginInfo>;
}

export interface SkillInfo {
  name: string;
  description: string;
  location: string;
  source: "bundled" | "plugin" | "project";
}
