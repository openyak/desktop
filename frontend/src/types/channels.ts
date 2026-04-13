/** Channel (messaging platform) types */

export interface ChannelInfo {
  id: string;
  name: string;
  status: string;  // "running" | "configured" | "disabled"
  type: string;
  account?: string;
}

export interface ChannelsResponse {
  channels: Record<string, ChannelInfo>;
  gateway_running: boolean;
  error?: string;
}

/** Status of the in-process channel system */
export interface ChannelSystemStatus {
  running: boolean;
  channels: Record<string, { enabled: boolean; running: boolean }>;
}

export interface PlatformDef {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
  auth: "qr" | "token";
  help: string;
  helpUrl?: string;
  fields?: { key: string; label: string; placeholder: string; secret?: boolean }[];
}
