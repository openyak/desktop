import type { PartData, ToolPart } from "@/types/message";

export interface Source {
  url: string;
  title: string;
  snippet?: string;
  favicon: string;
  domain: string;
}

interface SearchResult {
  url: string;
  title: string;
  snippet?: string;
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function getFavicon(url: string): string {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?sz=32&domain=${domain}`;
  } catch {
    return "";
  }
}

/**
 * Extract sources from a single tool part (web_search / web_fetch).
 */
export function extractSourcesFromTool(tool: ToolPart): Source[] {
  if (tool.state.status !== "completed") return [];
  const metadata = tool.state.metadata as Record<string, unknown> | null;
  if (!metadata) return [];

  const sources: Source[] = [];

  if (tool.tool === "web_search") {
    const results = metadata.results as SearchResult[] | undefined;
    if (Array.isArray(results)) {
      for (const r of results) {
        if (r.url) {
          sources.push({
            url: r.url,
            title: r.title || getDomain(r.url),
            snippet: r.snippet,
            favicon: getFavicon(r.url),
            domain: getDomain(r.url),
          });
        }
      }
    }
  } else if (tool.tool === "web_fetch") {
    const url = metadata.url as string | undefined;
    if (url) {
      sources.push({
        url,
        title: tool.state.title?.replace(/^Fetched\s+/, "") || getDomain(url),
        favicon: getFavicon(url),
        domain: getDomain(url),
      });
    }
  }

  return sources;
}

/**
 * Extract unique sources from tool parts (web_search + web_fetch).
 */
export function extractSources(parts: PartData[]): Source[] {
  const seen = new Set<string>();
  const sources: Source[] = [];

  for (const part of parts) {
    if (part.type !== "tool") continue;
    for (const s of extractSourcesFromTool(part as ToolPart)) {
      if (!seen.has(s.url)) {
        seen.add(s.url);
        sources.push(s);
      }
    }
  }

  return sources;
}
