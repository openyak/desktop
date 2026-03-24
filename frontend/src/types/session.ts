/** Session schemas — mirrors backend app/schemas/session.py */

export interface SessionCreate {
  project_id?: string | null;
  directory?: string | null;
  title?: string | null;
  agent?: string;
}

export interface SessionUpdate {
  title?: string | null;
  directory?: string | null;
  is_pinned?: boolean | null;
  time_archived?: string | null;
  permission?: Record<string, unknown> | null;
}

export interface SessionSearchResult {
  session: SessionResponse;
  snippet: string | null;
}

export interface SessionResponse {
  id: string;
  project_id: string | null;
  parent_id: string | null;
  slug: string | null;
  directory: string | null;
  title: string | null;
  version: number;
  summary_additions: number;
  summary_deletions: number;
  summary_files: number;
  summary_diffs: unknown[];
  is_pinned: boolean;
  permission: Record<string, unknown>;
  time_created: string;
  time_updated: string;
  time_compacting: string | null;
  time_archived: string | null;
}
