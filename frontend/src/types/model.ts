/** Provider & Model schemas — mirrors backend app/schemas/provider.py */

export interface ModelCapabilities {
  function_calling: boolean;
  vision: boolean;
  reasoning: boolean;
  json_output: boolean;
  max_context: number;
  max_output: number | null;
}

export interface ModelPricing {
  prompt: number;
  completion: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider_id: string;
  capabilities: ModelCapabilities;
  pricing: ModelPricing;
  metadata: Record<string, unknown>;
}

export interface ProviderStatus {
  status: "connected" | "error" | "unconfigured";
  model_count: number;
  error: string | null;
}
