"use client";

import { useEffect, useState, useCallback } from "react";
import { useTheme } from "next-themes";
import type mermaidAPI from "mermaid";

type Mermaid = typeof mermaidAPI;

let mermaidInstance: Mermaid | null = null;
let initPromise: Promise<Mermaid> | null = null;

export function useMermaid() {
  const [isReady, setIsReady] = useState(false);
  const { theme } = useTheme();

  // Initialize mermaid and configure theme
  useEffect(() => {
    const init = async () => {
      if (!mermaidInstance) {
        if (!initPromise) {
          initPromise = import("mermaid").then((mod) => mod.default);
        }
        mermaidInstance = await initPromise;
      }

      // Theme configuration - map to OpenYak theme colors
      const isDark = theme === "dark";
      mermaidInstance.initialize({
        startOnLoad: false,
        theme: "base",
        themeVariables: {
          // Primary colors
          primaryColor: isDark ? "#2F2F2F" : "#F5F5F5",
          primaryTextColor: isDark ? "#EFEFEF" : "#171717",
          primaryBorderColor: isDark ? "#424242" : "#E5E5E5",

          // Line and secondary colors
          lineColor: isDark ? "#525252" : "#D4D4D4",
          secondaryColor: isDark ? "#3D3D3D" : "#EBEBEB",
          tertiaryColor: isDark ? "#212121" : "#FFFFFF",

          // Text colors
          textColor: isDark ? "#EFEFEF" : "#171717",
          secondaryTextColor: isDark ? "#B4B4B4" : "#525252",

          // Background
          background: isDark ? "#212121" : "#FFFFFF",
          mainBkg: isDark ? "#2F2F2F" : "#F5F5F5",
          secondBkg: isDark ? "#3D3D3D" : "#EBEBEB",

          // Borders
          border1: isDark ? "#424242" : "#E5E5E5",
          border2: isDark ? "#525252" : "#D4D4D4",

          // Specific diagram elements
          nodeBorder: isDark ? "#525252" : "#D4D4D4",
          clusterBkg: isDark ? "#2F2F2F" : "#FAFAFA",
          clusterBorder: isDark ? "#424242" : "#E5E5E5",

          // For class diagrams
          classText: isDark ? "#EFEFEF" : "#171717",

          // For state diagrams
          labelColor: isDark ? "#EFEFEF" : "#171717",

          // For ER diagrams
          attributeBackgroundColorOdd: isDark ? "#2F2F2F" : "#FAFAFA",
          attributeBackgroundColorEven: isDark ? "#212121" : "#FFFFFF",
        },
      });

      setIsReady(true);
    };

    init();
  }, [theme]);

  const renderMermaid = useCallback(
    async (code: string): Promise<{ svg: string }> => {
      if (!mermaidInstance) {
        throw new Error("Mermaid not initialized");
      }

      const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
      const { svg } = await mermaidInstance.render(id, code);
      return { svg };
    },
    []
  );

  return {
    isReady,
    renderMermaid,
  };
}
