/** Connector (individual MCP server connection) types */

export interface ConnectorInfo {
  id: string;
  name: string;
  url: string;
  type: "remote" | "local";
  description: string;
  category: string;
  enabled: boolean;
  connected: boolean;
  status: "connected" | "disconnected" | "needs_auth" | "failed" | "disabled";
  error: string | null;
  tools_count: number;
  source: "builtin" | "custom";
  referenced_by: string[];
}

export interface ConnectorsResponse {
  connectors: Record<string, ConnectorInfo>;
}
