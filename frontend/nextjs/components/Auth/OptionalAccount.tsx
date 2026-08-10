"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/apiFetch";

type AuthMe = {
  user_id: string;
  kind: "visitor" | "registered" | string;
  is_new?: boolean;
  email?: string | null;
};

/**
 * Optional account sync — never blocks first use.
 * Login/register migrates visitor reports/sessions/docs server-side. :-)
 */
export default function OptionalAccount() {
  const [me, setMe] = useState<AuthMe | null>(null);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [migratedNote, setMigratedNote] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await apiFetch("/api/auth/me");
      if (!res.ok) return;
      const data = (await res.json()) as AuthMe;
      setMe(data);
    } catch {
      /* ignore bootstrap errors */
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setMigratedNote(null);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const res = await apiFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(
          typeof data?.detail === "string"
            ? data.detail
            : mode === "login"
              ? "登录失败"
              : "注册失败"
        );
        return;
      }
      const m = data?.migrated || {};
      const moved =
        (m.sessions || 0) + (m.jobs || 0) + (m.documents || 0) + (m.chunks || 0);
      if (moved > 0) {
        setMigratedNote(`已迁移 ${moved} 项游客数据到此账号`);
      }
      setMe({
        user_id: data.user_id,
        kind: data.kind || "registered",
        email: data.email,
      });
      setPassword("");
      setOpen(false);
    } catch {
      setError("网络错误");
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    setBusy(true);
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
      setMigratedNote(null);
      await refresh();
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  const label =
    me?.kind === "registered"
      ? me.email || "已登录"
      : me
        ? "游客"
        : "…";

  return (
    <div className="fixed top-3 right-3 z-[60]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-white/15 bg-black/40 px-3 py-1.5 text-xs text-white/90 backdrop-blur hover:bg-black/55"
        aria-expanded={open}
      >
        {label}
        {me?.kind !== "registered" ? " · 同步" : ""}
      </button>

      {open && (
        <div className="mt-2 w-72 rounded-lg border border-white/15 bg-[#111827]/95 p-3 text-sm text-white shadow-xl backdrop-blur">
          <p className="mb-2 text-xs text-white/70">
            登录仅用于跨设备同步，不是使用前提。
          </p>
          {me?.kind === "registered" ? (
            <div className="space-y-2">
              <p className="truncate text-xs text-teal-300">{me.email || me.user_id}</p>
              {migratedNote && (
                <p className="text-xs text-amber-200">{migratedNote}</p>
              )}
              <button
                type="button"
                disabled={busy}
                onClick={() => void logout()}
                className="w-full rounded bg-white/10 px-2 py-1.5 text-xs hover:bg-white/20 disabled:opacity-50"
              >
                退出（恢复游客）
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2 text-xs">
                <button
                  type="button"
                  className={mode === "login" ? "text-teal-300" : "text-white/50"}
                  onClick={() => setMode("login")}
                >
                  登录
                </button>
                <button
                  type="button"
                  className={mode === "register" ? "text-teal-300" : "text-white/50"}
                  onClick={() => setMode("register")}
                >
                  注册
                </button>
              </div>
              <input
                type="email"
                placeholder="邮箱"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded border border-white/15 bg-black/30 px-2 py-1.5 text-xs outline-none focus:border-teal-400"
              />
              <input
                type="password"
                placeholder="密码（至少 8 位）"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded border border-white/15 bg-black/30 px-2 py-1.5 text-xs outline-none focus:border-teal-400"
              />
              {error && <p className="text-xs text-red-300">{error}</p>}
              {migratedNote && (
                <p className="text-xs text-amber-200">{migratedNote}</p>
              )}
              <button
                type="button"
                disabled={busy || !email || password.length < (mode === "register" ? 8 : 1)}
                onClick={() => void submit()}
                className="w-full rounded bg-teal-600 px-2 py-1.5 text-xs font-medium hover:bg-teal-500 disabled:opacity-50"
              >
                {busy ? "处理中…" : mode === "login" ? "登录并迁移" : "注册并迁移"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
