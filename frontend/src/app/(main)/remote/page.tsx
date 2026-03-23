"use client";

import { useState, useEffect, useRef } from "react";
import { ArrowLeft, Wifi, WifiOff, QrCode, Copy, RefreshCw, Shield, Check, Loader2, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { API, IS_DESKTOP, getBackendUrl } from "@/lib/constants";

export default function RemotePage() {
  const { t } = useTranslation("settings");
  const [status, setStatus] = useState<{
    enabled: boolean;
    tunnel_url: string | null;
    token_preview: string | null;
    active_tasks: number;
    tunnel_mode: string;
    permission_mode: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [fullToken, setFullToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [permMode, setPermMode] = useState("auto");
  const [tunnelChanged, setTunnelChanged] = useState(false);
  const prevTunnelUrl = useRef<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await api.get<typeof status>(API.REMOTE.STATUS);
      setStatus(data);
      if (data) {
        setPermMode(data.permission_mode);

        // Detect tunnel URL change — show warning to re-scan QR
        if (prevTunnelUrl.current !== null && data.tunnel_url && data.tunnel_url !== prevTunnelUrl.current) {
          setTunnelChanged(true);
          // Auto-refresh QR code when URL changes
          if (showQr) {
            try {
              const backendUrl = IS_DESKTOP ? await getBackendUrl() : "";
              setQrUrl(`${backendUrl}${API.REMOTE.QR}?t=${Date.now()}`);
            } catch {}
          }
        }
        prevTunnelUrl.current = data.tunnel_url ?? null;
      }
    } catch {
      // Remote API not available
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  // Poll status every 30s to detect tunnel restarts
  useEffect(() => {
    if (!status?.enabled) return;
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, [status?.enabled]);

  const handleToggle = async () => {
    if (!status) return;
    setToggling(true);
    setTunnelChanged(false);
    try {
      if (status.enabled) {
        await api.post(API.REMOTE.DISABLE);
        setShowQr(false); setQrUrl(null); setFullToken(null);
        prevTunnelUrl.current = null;
      } else {
        const result = await api.post<{ token: string; tunnel_url: string | null }>(API.REMOTE.ENABLE);
        setFullToken(result.token);
        await fetchStatus();
        try {
          const backendUrl = IS_DESKTOP ? await getBackendUrl() : "";
          setQrUrl(`${backendUrl}${API.REMOTE.QR}?t=${Date.now()}`);
          setShowQr(true);
        } catch {}
        return;
      }
      await fetchStatus();
    } catch (err) {
      console.error("Failed to toggle remote access:", err);
    } finally {
      setToggling(false);
    }
  };

  const handleShowQr = async () => {
    if (showQr) { setShowQr(false); return; }
    try {
      const backendUrl = IS_DESKTOP ? await getBackendUrl() : "";
      setQrUrl(`${backendUrl}${API.REMOTE.QR}?t=${Date.now()}`);
      setShowQr(true);
      setTunnelChanged(false);
    } catch {}
  };

  const handleRotateToken = async () => {
    try {
      const result = await api.post<{ token: string }>(API.REMOTE.ROTATE_TOKEN);
      setFullToken(result.token);
      await fetchStatus();
      if (showQr) handleShowQr();
    } catch {}
  };

  const handleCopyUrl = () => {
    if (status?.tunnel_url) {
      navigator.clipboard.writeText(`${status.tunnel_url}/m`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handlePermModeChange = async (mode: string) => {
    setPermMode(mode);
    try { await api.patch(API.REMOTE.CONFIG, { permission_mode: mode }); } catch {}
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Button variant="ghost" size="icon" className="h-8 w-8 lg:hidden" asChild>
            <Link href="/c/new"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">{t("remote")}</h1>
        </div>

        {loading ? (
          <div className="h-16 rounded-lg bg-[var(--surface-tertiary)] animate-pulse" />
        ) : (
          <div className="space-y-6">
            <p className="text-xs text-[var(--text-secondary)]">{t("remoteDesc")}</p>

            {/* Tunnel URL changed warning */}
            {tunnelChanged && status?.enabled && (
              <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 animate-slide-up">
                <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-[var(--text-primary)]">Tunnel URL changed</p>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    The tunnel was restarted with a new URL. Mobile devices need to rescan the QR code to reconnect.
                  </p>
                </div>
                <Button variant="outline" size="sm" className="h-7 text-xs shrink-0" onClick={handleShowQr}>
                  <QrCode className="h-3 w-3 mr-1" />
                  Show QR
                </Button>
              </div>
            )}

            {/* Enable/Disable toggle */}
            <div className="flex items-center justify-between rounded-lg border border-[var(--border-default)] p-3">
              <div className="flex items-center gap-3">
                {toggling ? <Loader2 className="h-4 w-4 animate-spin text-[var(--text-secondary)]" /> : status?.enabled ? <Wifi className="h-4 w-4 text-green-500" /> : <WifiOff className="h-4 w-4 text-[var(--text-tertiary)]" />}
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{toggling ? t("remoteStarting") : status?.enabled ? t("remoteActive") : t("remoteDisabled")}</p>
                  {status?.enabled && status.tunnel_url && <p className="text-xs text-[var(--text-secondary)] truncate max-w-[280px]">{status.tunnel_url}</p>}
                </div>
              </div>
              <Switch checked={status?.enabled ?? false} onCheckedChange={handleToggle} disabled={toggling} />
            </div>

            {/* When enabled: show controls */}
            {status?.enabled && (
              <div className="space-y-3">
                {status.tunnel_url && (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 px-3 py-2 rounded-lg bg-[var(--surface-tertiary)] text-xs font-mono text-[var(--text-secondary)] truncate">{status.tunnel_url}/m</div>
                    <Button variant="outline" size="sm" className="h-8 shrink-0" onClick={handleCopyUrl}>
                      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      <span className="ml-1 text-xs">{copied ? t("remoteCopied") : t("remoteCopy")}</span>
                    </Button>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="h-8" onClick={handleShowQr}>
                    <QrCode className="h-3 w-3" /><span className="ml-1 text-xs">{showQr ? t("remoteHideQr") : t("remoteShowQr")}</span>
                  </Button>
                  <Button variant="outline" size="sm" className="h-8" onClick={handleRotateToken}>
                    <RefreshCw className="h-3 w-3" /><span className="ml-1 text-xs">{t("remoteRotateToken")}</span>
                  </Button>
                </div>

                {showQr && qrUrl && (
                  <div className="flex justify-center p-4 rounded-lg bg-white">
                    <img src={qrUrl} alt={t("remoteQrAlt")} className="w-48 h-48" style={{ imageRendering: "pixelated" }} />
                  </div>
                )}

                {fullToken && (
                  <div className="p-3 rounded-lg bg-[var(--surface-tertiary)] border border-[var(--border-default)]">
                    <p className="text-xs text-[var(--text-secondary)] mb-1">{t("remoteTokenLabel")}</p>
                    <code className="text-xs font-mono text-[var(--text-primary)] break-all select-all">{fullToken}</code>
                  </div>
                )}

                {!fullToken && status.token_preview && <p className="text-xs text-[var(--text-tertiary)]">{t("remoteTokenPreview", { preview: status.token_preview })}</p>}

                <div className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] p-3">
                  <Shield className="h-4 w-4 text-[var(--text-secondary)] shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{t("remotePermission")}</p>
                    <p className="text-xs text-[var(--text-secondary)]">{t("remotePermissionDesc")}</p>
                  </div>
                  <select value={permMode} onChange={(e) => handlePermModeChange(e.target.value)} className="px-2 py-1 rounded-md bg-[var(--surface-tertiary)] text-xs border border-[var(--border-default)] text-[var(--text-primary)]">
                    <option value="auto">{t("remotePermAuto")}</option>
                    <option value="ask">{t("remotePermAsk")}</option>
                    <option value="deny">{t("remotePermDeny")}</option>
                  </select>
                </div>

                {status.active_tasks > 0 && <p className="text-xs text-[var(--text-secondary)]">{t("remoteActiveTasks", { n: status.active_tasks })}</p>}
              </div>
            )}

            {!status?.enabled && (
              <div className="p-3 rounded-lg bg-[var(--surface-tertiary)] text-xs text-[var(--text-secondary)] space-y-1.5">
                <p>{t("remoteInstructions")}</p>
                <ol className="list-decimal list-inside space-y-0.5">
                  <li>{t("remoteStep1")}</li>
                  <li>{t("remoteStep2")}</li>
                  <li>{t("remoteStep3")}</li>
                </ol>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
