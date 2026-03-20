import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

// Lazy load heavy renderers to reduce initial bundle size
// These renderers include large dependencies (PDF.js, PPTX renderer, XLSX, React compiler)

export const PdfRenderer = dynamic(
  () => import("./pdf-renderer").then((m) => ({ default: m.PdfRenderer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full p-4">
        <Skeleton className="h-full w-full" />
      </div>
    ),
  }
);

export const PptxRenderer = dynamic(
  () => import("./pptx-renderer").then((m) => ({ default: m.PptxRenderer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full p-4">
        <Skeleton className="h-full w-full" />
      </div>
    ),
  }
);

export const XlsxRenderer = dynamic(
  () => import("./xlsx-renderer").then((m) => ({ default: m.XlsxRenderer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full p-4">
        <Skeleton className="h-full w-full" />
      </div>
    ),
  }
);

export const DocxRenderer = dynamic(
  () => import("./docx-renderer").then((m) => ({ default: m.DocxRenderer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full p-4">
        <Skeleton className="h-full w-full" />
      </div>
    ),
  }
);

export const ReactRenderer = dynamic(
  () => import("./react-renderer").then((m) => ({ default: m.ReactRenderer })),
  {
    loading: () => (
      <div className="flex items-center justify-center h-full p-4">
        <Skeleton className="h-full w-full" />
      </div>
    ),
  }
);
