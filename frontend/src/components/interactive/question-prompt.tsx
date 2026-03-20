"use client";

import { useState } from "react";
import { useTranslation } from 'react-i18next';
import { HelpCircle, Send } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import type { QuestionRequest } from "@/types/streaming";

interface QuestionPromptProps {
  question: QuestionRequest;
  onRespond: (answer: string) => void;
}

type QuestionOption = { label: string; description?: string };

function normalizeOptions(raw: unknown): QuestionOption[] {
  if (!Array.isArray(raw)) return [];
  const normalized: QuestionOption[] = [];

  for (const item of raw) {
    if (typeof item === "string") {
      const label = item.trim();
      if (label) normalized.push({ label });
      continue;
    }

    if (item && typeof item === "object") {
      const obj = item as Record<string, unknown>;
      const rawLabel = obj.label ?? obj.value ?? obj.title;
      if (typeof rawLabel !== "string") continue;
      const label = rawLabel.trim();
      if (!label) continue;
      const description = typeof obj.description === "string" ? obj.description : undefined;
      normalized.push({ label, description });
    }
  }

  return normalized;
}

export function QuestionPrompt({ question, onRespond }: QuestionPromptProps) {
  const { t } = useTranslation('chat');
  const [answer, setAnswer] = useState("");

  const questionText =
    (question.arguments?.question as string) ||
    (question.arguments?.questions as string) ||
    t('agentQuestion');

  const options = normalizeOptions(question.arguments?.options);

  const handleSubmit = () => {
    if (!answer.trim()) return;
    onRespond(answer);
    setAnswer("");
  };

  return (
    <div className="px-4 pb-3">
      <div className="mx-auto max-w-3xl xl:max-w-4xl">
        <div className="rounded-xl border-2 border-[var(--brand-primary)]/40 bg-[var(--brand-primary)]/5 p-4 animate-slide-up">
          <div className="flex items-start gap-3">
            <HelpCircle className="h-5 w-5 text-[var(--brand-primary)] shrink-0 mt-0.5" />
            <div className="flex-1 space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  {t('agentAsking')}
                </h3>
                <div className="text-sm text-[var(--text-secondary)] mt-1 prose prose-sm prose-invert max-w-none [&>p]:m-0">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {questionText}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Option buttons if available */}
              {options.length > 0 && (
                <div className="space-y-1.5">
                  {options.map((opt, i) => (
                    <button
                      key={`${opt.label}-${i}`}
                      onClick={() => onRespond(opt.label)}
                      className="w-full text-left rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] px-3 py-2 text-sm hover:bg-[var(--surface-tertiary)] transition-colors"
                    >
                      <span className="font-medium text-[var(--text-primary)]">
                        {opt.label}
                      </span>
                      {opt.description && (
                        <span className="block text-xs text-[var(--text-tertiary)] mt-0.5">
                          {opt.description}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* Free-text input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                  placeholder={t('typeAnswer')}
                  className="flex-1 rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[var(--ring)]"
                />
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  disabled={!answer.trim()}
                  className="gap-1.5"
                >
                  <Send className="h-3.5 w-3.5" />
                  {t('submit')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
