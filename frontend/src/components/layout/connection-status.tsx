"use client";

import { WifiOff, RefreshCw } from "lucide-react";
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from "framer-motion";
import { useConnectionStore } from "@/stores/connection-store";

export function ConnectionStatus() {
  const { t } = useTranslation('common');
  const status = useConnectionStore((s) => s.status);

  const showBanner = status === "reconnecting" || status === "disconnected";

  return (
    <AnimatePresence>
      {showBanner && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="overflow-hidden"
        >
          <div className={`flex items-center justify-center gap-2 px-4 py-1.5 text-xs font-medium ${
            status === "disconnected"
              ? "bg-[var(--color-destructive)]/10 text-[var(--color-destructive)]"
              : "bg-[var(--color-warning)]/10 text-[var(--color-warning)]"
          }`}>
            {status === "reconnecting" ? (
              <>
                <RefreshCw className="h-3 w-3 animate-spin" />
                <span>{t('reconnecting')}</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                <span>{t('connectionLost')}</span>
              </>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
