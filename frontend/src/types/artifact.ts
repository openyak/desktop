/** Artifact types — for the artifact preview panel. */

export type ArtifactType =
  | "react"
  | "html"
  | "svg"
  | "code"
  | "markdown"
  | "mermaid"
  | "docx"
  | "xlsx"
  | "pdf"
  | "pptx"
  | "csv"
  | "file-preview";

export interface Artifact {
  /** Unique ID (tool call_id or generated hash). */
  id: string;
  /** Display title shown in the panel header. */
  title: string;
  /** Determines which renderer to use. */
  type: ArtifactType;
  /** Raw content (source code, markup, etc.). */
  content: string;
  /** Programming language (for code/react types). */
  language?: string;
  /** File path on disk (for file-preview type). */
  filePath?: string;
  /** Identifier for updating the same artifact across iterations. */
  identifier?: string;
}
