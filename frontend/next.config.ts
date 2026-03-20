import type { NextConfig } from "next";
import path from "path";

const isDesktopBuild = process.env.DESKTOP_BUILD === "true";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },

  // Static export for Electron desktop builds
  ...(isDesktopBuild && {
    output: "export",
    images: { unoptimized: true },
  }),

  // API proxy rewrites (only needed in web mode, not in static export)
  ...(!isDesktopBuild && {
    async rewrites() {
      return [
        {
          source: "/api/:path*",
          destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
        },
        {
          source: "/health",
          destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`,
        },
      ];
    },
  }),
};

export default nextConfig;
