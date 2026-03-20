"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  Gift,
  RotateCcw,
  Loader2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { OpenYakLogo } from "@/components/ui/openyak-logo";
import { useAuthStore } from "@/stores/auth-store";
import { proxyApi } from "@/lib/proxy-api";
import { IS_DESKTOP } from "@/lib/constants";
import { desktopAPI } from "@/lib/tauri-api";
import { toast } from "sonner";

// ── Types ────────────────────────────────────────────────────────────────

interface BalanceData {
  credits: number;
  usd_equivalent: number;
  daily_free_tokens_used: number;
  daily_free_token_limit: number;
}

interface CreditPack {
  id: string;
  credits: number;
  price_usd: number;
  label: string;
}

interface TransactionItem {
  id: string;
  amount: number;
  balance_after: number;
  type: string;
  description: string;
  metadata: Record<string, unknown> | null;
  time_created: string;
}

interface TransactionsData {
  items: TransactionItem[];
  total: number;
}

interface GroupedTransaction {
  id: string;
  amount: number;
  balance_after: number;
  type: string;
  description: string;
  time_created: string;
  count: number;
}

type PaymentChannel = "card" | "alipay";

const TX_PAGE_SIZE = 20;
const GROUP_WINDOW_MS = 2 * 60 * 1000; // 2 minutes

// ── Helpers ──────────────────────────────────────────────────────────────

function formatCredits(credits: number): string {
  if (credits === 0) return "0";
  if (credits >= 1000) return `${(credits / 1000).toFixed(1)}K`;
  return credits.toFixed(0);
}

function formatWholeCredits(value: number): string {
  if (Math.abs(value) < 1 && value !== 0) {
    const abs = Math.abs(value);
    if (abs < 0.001) return value < 0 ? "-<0.001" : "+<0.001";
    return value.toFixed(3);
  }
  const rounded = Math.round(value);
  return String(Object.is(rounded, -0) ? 0 : rounded);
}

function formatSignedWholeCredits(value: number): string {
  if (Math.abs(value) < 1 && value !== 0) {
    const abs = Math.abs(value);
    if (abs < 0.001) return value < 0 ? "-<0.001" : "+<0.001";
    return `${value > 0 ? "+" : ""}${value.toFixed(3)}`;
  }
  const rounded = Math.round(value);
  const normalized = Object.is(rounded, -0) ? 0 : rounded;
  return `${normalized > 0 ? "+" : ""}${normalized}`;
}

function transactionIcon(type: string) {
  switch (type) {
    case "purchase":
      return ArrowUpRight;
    case "usage":
      return ArrowDownRight;
    case "bonus":
      return Gift;
    case "refund":
      return RotateCcw;
    default:
      return CreditCard;
  }
}

function transactionColor(type: string): string {
  switch (type) {
    case "purchase":
    case "bonus":
    case "refund":
      return "text-[var(--color-success)]";
    case "usage":
      return "text-[var(--color-destructive)]";
    default:
      return "text-[var(--text-secondary)]";
  }
}

function mergeGroup(group: TransactionItem[]): GroupedTransaction {
  if (group.length === 1) {
    return { ...group[0], count: 1 };
  }

  const totalAmount = group.reduce((sum, tx) => sum + tx.amount, 0);
  // Items are desc sorted — first item is the most recent
  const latestBalanceAfter = group[0].balance_after;
  const latestTime = group[0].time_created;

  // Build description
  const chatModels = new Set<string>();
  let toolCount = 0;

  for (const tx of group) {
    if (tx.description.startsWith("Chat:")) {
      chatModels.add(tx.description.replace("Chat: ", ""));
    } else if (tx.description.startsWith("Tool:")) {
      toolCount++;
    }
  }

  let description: string;
  if (chatModels.size > 0 && toolCount > 0) {
    const model = [...chatModels][0];
    description = `Chat: ${model} + ${toolCount} tool${toolCount > 1 ? "s" : ""}`;
  } else if (chatModels.size > 0) {
    const model = [...chatModels][0];
    const chatCount = group.length - toolCount;
    description = chatCount > 1 ? `Chat: ${model} (${chatCount} steps)` : `Chat: ${model}`;
  } else if (toolCount > 0) {
    const toolNames = new Set<string>();
    for (const tx of group) {
      if (tx.description.startsWith("Tool:")) {
        toolNames.add(tx.description.replace("Tool: ", ""));
      }
    }
    const name = [...toolNames][0];
    description = toolCount > 1 ? `Tool: ${name} (\u00d7${toolCount})` : `Tool: ${name}`;
  } else {
    description = group[0].description;
  }

  return {
    id: group[0].id,
    amount: totalAmount,
    balance_after: latestBalanceAfter,
    type: group[0].type,
    description,
    time_created: latestTime,
    count: group.length,
  };
}

function groupTransactions(items: TransactionItem[]): GroupedTransaction[] {
  if (items.length === 0) return [];

  const result: GroupedTransaction[] = [];
  let group: TransactionItem[] = [items[0]];

  for (let i = 1; i < items.length; i++) {
    const tx = items[i];
    const lastInGroup = group[group.length - 1];
    const timeDiff = Math.abs(
      new Date(lastInGroup.time_created).getTime() -
        new Date(tx.time_created).getTime(),
    );

    if (
      tx.type === "usage" &&
      lastInGroup.type === "usage" &&
      timeDiff <= GROUP_WINDOW_MS
    ) {
      group.push(tx);
    } else {
      result.push(mergeGroup(group));
      group = [tx];
    }
  }
  result.push(mergeGroup(group));

  return result;
}

// ── Main Page ────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { t } = useTranslation('billing');
  const router = useRouter();
  const { isConnected, proxyUrl, user, updateUser } = useAuthStore();
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [paymentChannel, setPaymentChannel] = useState<PaymentChannel>("card");
  const [txPage, setTxPage] = useState(0);

  const checkoutReturnBase = proxyUrl
    ? `${proxyUrl.replace(/\/$/, "")}/api/billing/checkout-return`
    : "https://museproxy.doxmind.com/api/billing/checkout-return";

  const { data: balance, isLoading: balanceLoading, refetch: balanceRefetch } = useQuery({
    queryKey: ["billing", "balance"],
    queryFn: () => proxyApi.get<BalanceData>("/api/billing/balance"),
    enabled: isConnected,
    refetchInterval: 30_000,
  });

  const { data: packs, isLoading: packsLoading } = useQuery({
    queryKey: ["billing", "packs"],
    queryFn: () => proxyApi.get<CreditPack[]>("/api/billing/packs"),
    enabled: isConnected,
    staleTime: 60 * 60 * 1000,
  });

  const {
    data: transactions,
    isLoading: txLoading,
    isPlaceholderData: txPlaceholder,
    refetch: txRefetch,
  } = useQuery({
    queryKey: ["billing", "transactions", txPage],
    queryFn: () => proxyApi.get<TransactionsData>(
      `/api/billing/transactions?limit=${TX_PAGE_SIZE}&offset=${txPage * TX_PAGE_SIZE}`
    ),
    enabled: isConnected,
    placeholderData: (prev) => prev,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const checkout = new URLSearchParams(window.location.search).get("checkout");
    if (!checkout) return;

    if (checkout === "success") {
      toast.success("Payment completed. Refreshing your balance...");
      void balanceRefetch();
      void txRefetch();
    } else if (checkout === "cancel") {
      toast.message("Checkout cancelled.");
    }

    router.replace("/billing");
  }, [router, balanceRefetch, txRefetch]);

  const checkoutMutation = useMutation({
    mutationFn: async ({
      packId,
      channel,
    }: {
      packId: string;
      channel: PaymentChannel;
    }) => {
      setCheckoutError(null);
      const result = await proxyApi.post<{ checkout_url: string }>(
        "/api/billing/create-checkout",
        {
          pack_id: packId,
          payment_channel: channel,
          success_url: `${checkoutReturnBase}?checkout=success`,
          cancel_url: `${checkoutReturnBase}?checkout=cancel`,
        },
      );
      return result;
    },
    onSuccess: async (data) => {
      if (IS_DESKTOP) {
        await desktopAPI.openExternal(data.checkout_url);
        return;
      }
      window.open(data.checkout_url, "_blank", "noopener,noreferrer");
    },
    onError: (err: Error) => {
      setCheckoutError(err.message || "Failed to create checkout session");
    },
  });

  useEffect(() => {
    if (!balance || !user) return;
    const nextBillingMode = balance.credits > 0 ? "credits" : user.billing_mode;
    const unchanged =
      user.billing_mode === nextBillingMode &&
      user.credit_balance === balance.credits &&
      user.daily_free_tokens_used === balance.daily_free_tokens_used &&
      user.daily_free_token_limit === balance.daily_free_token_limit;
    if (unchanged) return;

    updateUser({
      ...user,
      billing_mode: nextBillingMode,
      credit_balance: balance.credits,
      daily_free_tokens_used: balance.daily_free_tokens_used,
      daily_free_token_limit: balance.daily_free_token_limit,
    });
  }, [balance, user, updateUser]);

  // Not connected — redirect prompt
  if (!isConnected) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl px-4 py-8">
          <div className="flex items-center gap-3 mb-8">
            <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" asChild>
              <Link href="/c/new">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-lg font-semibold text-[var(--text-primary)]">{t('title')}</h1>
          </div>
          <div className="text-center py-20">
            <OpenYakLogo size={40} className="text-[var(--text-tertiary)] mx-auto mb-3" />
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              {t('connectPrompt')}
            </p>
            <Button variant="outline" size="sm" asChild>
              <Link href="/settings">{t('goToSettings')}</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" asChild>
            <Link href="/c/new">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">{t('title')}</h1>
        </div>

        <div className="space-y-8">
          {/* Balance Overview */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">{t('balance')}</h2>
            {balanceLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 rounded-xl" />
              </div>
            ) : balance ? (
              <div className="space-y-3">
                {/* Credit Balance Card */}
                <div className="rounded-xl border border-[var(--border-default)] p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <CreditCard className="h-4 w-4 text-[var(--text-tertiary)]" />
                    <span className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">
                      {t('credits')}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-semibold text-[var(--text-primary)] font-mono">
                      {formatCredits(balance.credits)}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
          </section>

          <Separator />

          {/* Credit Packs */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
              {t('buyCredits')}
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mb-3">
              {t('buyCreditsDesc')}
            </p>
            <div className="mb-3 rounded-xl border border-[var(--border-default)] p-2">
              <div className="text-[11px] text-[var(--text-tertiary)] mb-2">{t('paymentMethod')}</div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPaymentChannel("card")}
                  className={`rounded-lg border px-3 py-2 text-xs text-left transition-colors ${
                    paymentChannel === "card"
                      ? "border-[var(--brand-primary)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                      : "border-[var(--border-default)] text-[var(--text-secondary)]"
                  }`}
                >
                  {t('internationalCard')}
                </button>
                <button
                  type="button"
                  onClick={() => setPaymentChannel("alipay")}
                  className={`rounded-lg border px-3 py-2 text-xs text-left transition-colors ${
                    paymentChannel === "alipay"
                      ? "border-[var(--brand-primary)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                      : "border-[var(--border-default)] text-[var(--text-secondary)]"
                  }`}
                >
                  {t('alipay')}
                </button>
              </div>
              {paymentChannel === "alipay" && (
                <p className="mt-2 text-[11px] text-[var(--text-tertiary)]">
                  {t('alipayNote')}
                </p>
              )}
            </div>
            {packsLoading ? (
              <div className="grid grid-cols-3 gap-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-32 rounded-xl" />
                ))}
              </div>
            ) : packs ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {packs.map((pack, i) => (
                  <button
                    key={pack.id}
                    onClick={() => checkoutMutation.mutate({ packId: pack.id, channel: paymentChannel })}
                    disabled={checkoutMutation.isPending}
                    className={`relative rounded-xl border p-4 text-left transition-colors hover:bg-[var(--surface-secondary)] ${
                      i === 1
                        ? "border-[var(--brand-primary)] ring-1 ring-[var(--brand-primary)]"
                        : "border-[var(--border-default)]"
                    }`}
                  >
                    {i === 1 && (
                      <span className="absolute -top-2.5 left-3 bg-[var(--brand-primary)] text-[var(--brand-primary-text)] text-[10px] font-semibold px-2 py-0.5 rounded-full">
                        {t('popular')}
                      </span>
                    )}
                    <div className="text-2xl font-semibold text-[var(--text-primary)] font-mono">
                      {formatCredits(pack.credits)}
                    </div>
                    <div className="text-xs text-[var(--text-tertiary)] mt-0.5">{t('creditsLabel')}</div>
                    <div className="text-lg font-semibold text-[var(--text-primary)] mt-3">
                      ${pack.price_usd.toFixed(2)}
                    </div>
                  </button>
                ))}
              </div>
            ) : null}

            {checkoutMutation.isPending && (
              <div className="flex items-center gap-2 mt-3 text-xs text-[var(--text-secondary)]">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{t('openingCheckout')}</span>
              </div>
            )}

            {checkoutError && (
              <div className="flex items-center gap-1.5 mt-3 text-xs text-[var(--color-destructive)]">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                <span>{checkoutError}</span>
              </div>
            )}
          </section>

          <Separator />

          {/* Transaction History */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
              {t('transactionHistory')}
            </h2>
            {txLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 rounded-lg" />
                ))}
              </div>
            ) : transactions && transactions.items.length > 0 ? (
              <>
                <div className={`rounded-xl border border-[var(--border-default)] overflow-hidden transition-opacity ${txPlaceholder ? "opacity-60" : ""}`}>
                  {groupTransactions(transactions.items).map((tx, i) => {
                    const Icon = transactionIcon(tx.type);
                    return (
                      <div
                        key={tx.id}
                        className={`flex items-center gap-3 px-3 py-2.5 ${
                          i > 0 ? "border-t border-[var(--border-default)]" : ""
                        }`}
                      >
                        <Icon className={`h-4 w-4 shrink-0 ${transactionColor(tx.type)}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-[var(--text-primary)] truncate">
                            {tx.description}
                          </p>
                          <p className="text-[10px] text-[var(--text-tertiary)]">
                            {new Date(tx.time_created).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className={`text-xs font-mono font-medium ${transactionColor(tx.type)}`}>
                            {formatSignedWholeCredits(tx.amount)}
                          </p>
                          <p className="text-[10px] text-[var(--text-tertiary)] font-mono">
                            {t('bal')}: {formatWholeCredits(tx.balance_after)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {/* Pagination */}
                {transactions.total > TX_PAGE_SIZE && (() => {
                  const totalPages = Math.ceil(transactions.total / TX_PAGE_SIZE);
                  return (
                    <div className="flex items-center justify-between mt-3">
                      <button
                        onClick={() => setTxPage((p) => Math.max(0, p - 1))}
                        disabled={txPage === 0}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition-colors text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] disabled:opacity-30 disabled:pointer-events-none"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                        {t('prevPage')}
                      </button>
                      <span className="text-xs text-[var(--text-tertiary)] font-mono">
                        {t('pageIndicator', { current: txPage + 1, total: totalPages })}
                      </span>
                      <button
                        onClick={() => setTxPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={txPage >= totalPages - 1}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition-colors text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] disabled:opacity-30 disabled:pointer-events-none"
                      >
                        {t('nextPage')}
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })()}
              </>
            ) : (
              <div className="text-center py-8">
                <p className="text-xs text-[var(--text-tertiary)]">
                  {t('noTransactions')}
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
