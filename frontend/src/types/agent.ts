/** Agent schemas — mirrors backend app/schemas/agent.py */

export interface PermissionRule {
  action: "allow" | "deny" | "ask";
  pattern: string;
}

export interface Ruleset {
  rules: PermissionRule[];
}

export interface AgentInfo {
  name: string;
  description: string;
  mode: "primary" | "subagent" | "hidden";
  tools: string[];
  permissions: Ruleset;
  system_prompt?: string | null;
  temperature?: number | null;
  metadata: Record<string, unknown>;
}
