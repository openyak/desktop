"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";

interface ChatActionsProps {
  isGenerating: boolean;
  canSend: boolean;
  onSend: () => void;
  onStop: () => void;
}

export function ChatActions({ isGenerating, canSend, onSend, onStop }: ChatActionsProps) {
  const showButton = isGenerating || canSend;

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center gap-1">
        <AnimatePresence>
          {showButton && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="default"
                    size="icon"
                    className="h-8 w-8 rounded-full"
                    onClick={isGenerating ? onStop : onSend}
                  >
                    <AnimatePresence mode="wait" initial={false}>
                      <motion.span
                        key={isGenerating ? "stop" : "send"}
                        initial={{ rotate: -90, opacity: 0 }}
                        animate={{ rotate: 0, opacity: 1 }}
                        exit={{ rotate: 90, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="flex items-center justify-center"
                      >
                        {isGenerating ? (
                          <Square className="h-3.5 w-3.5 fill-current" />
                        ) : (
                          <ArrowUp className="h-[18px] w-[18px]" />
                        )}
                      </motion.span>
                    </AnimatePresence>
                    <span className="sr-only">
                      {isGenerating ? "Stop generation" : "Send message"}
                    </span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {isGenerating ? "Stop generation" : "Send message (Enter)"}
                </TooltipContent>
              </Tooltip>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </TooltipProvider>
  );
}
