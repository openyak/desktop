"use client";

import { AlertCircle, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface InlineErrorProps {
  message: string;
  visible: boolean;
  onDismiss?: () => void;
}

export function InlineError({ message, visible, onDismiss }: InlineErrorProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="overflow-hidden"
          role="alert"
        >
          <div className="flex items-center gap-2 text-xs text-[var(--color-destructive)] py-1.5">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{message}</span>
            {onDismiss && (
              <button onClick={onDismiss} className="shrink-0" aria-label="Dismiss error">
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
