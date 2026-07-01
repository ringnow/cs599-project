/** useApi — 统一的 API 请求 Hook */
import { useState, useRef, useCallback } from "react";
import { Tab, HistoryItem } from "../types";

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export interface UseApiOptions {
  apiUrl: string;
  apiKey: string;
  selectedProvider: string;
  selectedModel: string;
}

export function useApi(opts: UseApiOptions) {
  const [isLoading, setIsLoading] = useState(false);
  const [progressLogs, setProgressLogs] = useState<string[]>([]);
  const [executionSteps, setExecutionSteps] = useState<any[]>([]);
  const [currentMarkdown, setCurrentMarkdown] = useState("");
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentRequestIdRef = useRef("");

  const getRequestHeaders = useCallback((): Record<string, string> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    // JWT token is the sole backend auth mechanism — read from localStorage
    // so useApi stays in sync with login/logout without prop-drilling.
    const token = localStorage.getItem("cs599_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  }, []);

  const getRequestUrl = useCallback((endpoint: string) => {
    const base = opts.apiUrl.trim().replace(/\/$/, "");
    return base ? `${base}/api${endpoint}` : `/api${endpoint}`;
  }, [opts.apiUrl]);

  const clearAllTimers = useCallback(() => {
    timerRefs.current.forEach(clearTimeout);
    timerRefs.current = [];
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const stopExecution = useCallback(() => {
    clearAllTimers();
    const rid = currentRequestIdRef.current;
    if (rid) fetch(`/api/cancel/${rid}`, { method: "POST" }).catch(() => {});
    setIsLoading(false);
    setProgressLogs(prev => [...prev, "⚠️ 已由用户手动中断执行。"]);
  }, [clearAllTimers]);

  interface RunTaskParams {
    taskType: Tab;
    requestBody: Record<string, any>;
    endpoint: string;
    activeTitle: string;
    onAgentExchanges?: (ex: any[]) => void;
    onHistoryReports?: () => void;
    showToast: (msg: string) => void;
    onRequestId?: (id: string) => void;
  }

  const runTask = useCallback(async (params: RunTaskParams) => {
    const { taskType, requestBody, endpoint, activeTitle, onAgentExchanges, onHistoryReports, showToast, onRequestId } = params;
    if (isLoading) return;
    clearAllTimers();
    setIsLoading(true);
    setProgressLogs([]);
    setCurrentMarkdown("");

    setProgressLogs(["📡 正在连接后端...", "📊 正在发送请求..."]);
    const addMsg = (msg: string) => setProgressLogs(prev => [...prev, msg]);

    const requestId = "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    currentRequestIdRef.current = requestId;
    onRequestId?.(requestId);

    let beatCount = 0;
    const heartbeatId = setInterval(() => {
      beatCount++;
      addMsg(`⏳ 模型正在处理... (${beatCount * 15}s)`);
    }, 15000);
    timerRefs.current.push(heartbeatId as unknown as ReturnType<typeof setTimeout>);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await fetch(getRequestUrl(endpoint), {
        method: "POST",
        headers: getRequestHeaders(),
        body: JSON.stringify({ ...requestBody, request_id: requestId }),
        signal: controller.signal,
      });

      timerRefs.current.forEach(clearTimeout);
      timerRefs.current = [];

      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try { const ed = await res.json(); errMsg = ed.message || ed.detail || errMsg; } catch {}
        if (res.status === 401) throw new AuthError(errMsg);
        throw new HttpError(res.status, errMsg);
      }

      const data = await res.json();
      setProgressLogs([]);
      setExecutionSteps(data.steps || []);

      if (data.logs?.length) {
        data.logs.forEach((logItem: string, idx: number) => {
          setTimeout(() => setProgressLogs(prev => [...prev, logItem]), (idx + 1) * 300);
        });
      }

      const delayMs = (data.logs ? data.logs.length * 300 : 300) + 200;
      setTimeout(() => {
        if (taskType === "agents" && data.exchange) onAgentExchanges?.(data.exchange);
        setCurrentMarkdown(data.markdown || "");
        onHistoryReports?.();
        setIsLoading(false);
        showToast("生成成功，已记录至历史存档");
      }, delayMs);

    } catch (err: any) {
      clearAllTimers();
      if (err?.name === "AbortError") {
        addMsg("⏱️ 请求超时或已取消");
        setCurrentMarkdown("### ⏱️ 请求超时\n\n后端处理超时，请求已被中止。");
      } else if (err instanceof AuthError) {
        addMsg("🔑 认证失败: API Key 无效");
        setCurrentMarkdown("### 🔑 API Key 认证失败\n\n请检查服务商配置。");
      } else if (err instanceof HttpError) {
        addMsg(`🔴 HTTP ${err.status}: ${err.message}`);
        setCurrentMarkdown(`### ⚠️ 请求失败 [HTTP ${err.status}]\n${err.message}`);
      } else {
        addMsg(`🔴 ${err.message || "未知错误"}`);
        setCurrentMarkdown(`### ⚠️ 请求失败\n${err.message || "未知错误"}`);
      }
      setIsLoading(false);
    }
  }, [isLoading, clearAllTimers, getRequestUrl, getRequestHeaders]);

  return {
    isLoading, setIsLoading,
    progressLogs, setProgressLogs,
    executionSteps, setExecutionSteps,
    currentMarkdown, setCurrentMarkdown,
    clearAllTimers,
    stopExecution,
    runTask,
    currentRequestIdRef,
    abortControllerRef,
    timerRefs,
    getRequestUrl,
    getRequestHeaders,
  };
}