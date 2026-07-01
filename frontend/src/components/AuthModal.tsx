import { useState } from "react";
import { X, LogIn, UserPlus } from "lucide-react";

interface AuthModalProps {
  onClose: () => void;
  onLogin: (token: string, username: string) => void;
}

const MIN_PASSWORD_LENGTH = 4;

export function AuthModal({ onClose, onLogin }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [notice, setNotice] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setNotice(null);
    if (mode === "register" && password.length < MIN_PASSWORD_LENGTH) {
      setNotice({ kind: "error", text: `密码至少 ${MIN_PASSWORD_LENGTH} 个字符` });
      return;
    }
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/api/login" : "/api/register";
      const body = mode === "login"
        ? { username, password }
        : { username, password, email };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Request failed");
      }

      if (mode === "login") {
        const d = await res.json();
        localStorage.setItem("cs599_token", d.access_token);
        localStorage.setItem("cs599_username", d.username);
        onLogin(d.access_token, d.username);
      } else {
        setMode("login");
        setUsername("");
        setPassword("");
        setEmail("");
        setNotice({ kind: "success", text: "注册成功，请登录。" });
      }
    } catch (e: any) {
      setNotice({ kind: "error", text: e.message });
    } finally {
      setLoading(false);
    }
  };

  const passwordMeetsMin = mode !== "register" || password.length >= MIN_PASSWORD_LENGTH;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-96 max-w-[90vw]" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-slate-800">
            {mode === "login" ? "Login" : "Register"}
          </h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Notice (error or success) */}
        {notice && (
          <div className={`mb-4 p-3 rounded-lg text-sm ${notice.kind === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
            {notice.text}
          </div>
        )}

        {/* Form */}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400"
              placeholder="Enter username"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Email (optional)</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400"
                placeholder="email@example.com"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && passwordMeetsMin && handleSubmit()}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400"
              placeholder={mode === "register" ? `Min ${MIN_PASSWORD_LENGTH} characters` : "Enter password"}
            />
          </div>
        </div>

        {/* Buttons */}
        <button
          onClick={handleSubmit}
          disabled={loading || !username || !password || !passwordMeetsMin}
          className="w-full mt-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium text-sm hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 transition flex items-center justify-center gap-2"
        >
          {loading ? (
            <span className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
          ) : mode === "login" ? (
            <LogIn className="w-4 h-4" />
          ) : (
            <UserPlus className="w-4 h-4" />
          )}
          {mode === "login" ? "Login" : "Register"}
        </button>

        <p className="text-center text-xs text-slate-400 mt-3">
          {mode === "login" ? (
            <>No account? <button onClick={() => { setMode("register"); setNotice(null); }} className="text-indigo-600 hover:underline">Register</button></>
          ) : (
            <>Already have an account? <button onClick={() => { setMode("login"); setNotice(null); }} className="text-indigo-600 hover:underline">Login</button></>
          )}
        </p>

        {mode === "login" && (
          <p className="text-center text-[10px] text-slate-300 mt-1">未注册？点击下方 Register 创建账号</p>
        )}
      </div>
    </div>
  );
}
