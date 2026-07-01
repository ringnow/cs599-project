/** 系统设置 Tab */
import React, { useState, useEffect } from "react";
import { Server, Database, Zap } from "lucide-react";
import { apiFetch } from "../utils/api";

interface Props {
  latexEnabled: boolean;
  setLatexEnabled: (v: boolean) => void;
  persistEnabled: boolean;
  setPersistEnabled: (v: boolean) => void;
}

export function SettingsTab({ latexEnabled, setLatexEnabled, persistEnabled, setPersistEnabled }: Props) {
  const [cacheStatus, setCacheStatus] = useState<any>(null);
  const [dbStatus, setDbStatus] = useState<any>(null);

  const fetchSystemStatus = async () => {
    try {
      const cRes = await apiFetch("/api/cache/stats");
      if (cRes.ok) setCacheStatus(await cRes.json());
    } catch (_) {}
    try {
      const dRes = await apiFetch("/api/search-history/stats");
      if (dRes.ok) setDbStatus(await dRes.json());
    } catch (_) {}
  };

  useEffect(() => { fetchSystemStatus(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">系统偏好设置 🛠️</h2>
        <p className="text-xs text-gray-500 leading-relaxed font-sans">调节学术格式化模版与全局提示语约束，自定义您的研写系统习惯。</p>
      </div>
      <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex flex-col select-none">
            <span className="text-xs font-semibold text-gray-800">LaTeX 公式高保真排版</span>
            <span className="text-[10px] text-gray-400">优先采用严格的学术数学符号记号</span>
          </div>
          <div onClick={() => { setLatexEnabled(!latexEnabled); localStorage.setItem("cs599_latex", String(!latexEnabled)); }} className={`w-9 h-5 rounded-full flex p-0.5 border cursor-pointer transition-all ${latexEnabled ? 'bg-indigo-600 justify-end border-indigo-500' : 'bg-gray-200 justify-start border-gray-300'}`}>
            <div className="w-3.5 h-3.5 bg-white rounded-full shadow-md"></div>
          </div>
        </div>
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="flex flex-col select-none">
            <span className="text-xs font-semibold text-gray-800">学术历史本地持久化</span>
            <span className="text-[10px] text-gray-400">允许浏览器本地缓存您在工作站研讨记录</span>
          </div>
          <div onClick={() => { setPersistEnabled(!persistEnabled); localStorage.setItem("cs599_persist", String(!persistEnabled)); }} className={`w-9 h-5 rounded-full flex p-0.5 border cursor-pointer transition-all ${persistEnabled ? 'bg-indigo-600 justify-end border-indigo-500' : 'bg-gray-200 justify-start border-gray-300'}`}>
            <div className="w-3.5 h-3.5 bg-white rounded-full shadow-md"></div>
          </div>
        </div>
      </div>

      {/* System Status Section */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Server className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-bold text-gray-800">系统服务状态</h3>
          <button onClick={fetchSystemStatus} className="text-[10px] text-indigo-600 hover:text-indigo-800 ml-auto">刷新</button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {/* Cache Status */}
          <div className="border border-gray-200 rounded-xl bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Zap className={`w-4 h-4 ${cacheStatus?.enabled ? 'text-green-500' : 'text-gray-300'}`} />
              <span className="text-xs font-semibold text-gray-700">Redis 缓存</span>
              <span className={`ml-auto w-2 h-2 rounded-full ${cacheStatus?.enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
            </div>
            {cacheStatus?.enabled ? (
              <div className="space-y-1 text-[10px] text-gray-500">
                <div className="flex justify-between"><span>缓存键数量</span><span className="font-mono text-gray-700">{cacheStatus.cached_keys ?? '-'}</span></div>
                <div className="flex justify-between"><span>内存占用</span><span className="font-mono text-gray-700">{cacheStatus.memory_used_mb} MB</span></div>
              </div>
            ) : (
              <p className="text-[10px] text-gray-400">未连接（设置 REDIS_URL 环境变量启用）</p>
            )}
          </div>

          {/* DB Status */}
          <div className="border border-gray-200 rounded-xl bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-green-500" />
              <span className="text-xs font-semibold text-gray-700">搜索数据库</span>
              <span className="ml-auto w-2 h-2 rounded-full bg-green-500" />
            </div>
            {dbStatus ? (
              <div className="space-y-1 text-[10px] text-gray-500">
                <div className="flex justify-between"><span>总搜索次数</span><span className="font-mono text-gray-700">{dbStatus.total_searches}</span></div>
                <div className="flex justify-between"><span>平均耗时</span><span className="font-mono text-gray-700">{dbStatus.avg_duration_seconds?.toFixed(1)}s</span></div>
                <div className="flex justify-between"><span>总引用论文</span><span className="font-mono text-gray-700">{dbStatus.total_papers_cited}</span></div>
              </div>
            ) : (
              <p className="text-[10px] text-gray-400">加载中...</p>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 bg-amber-50 border border-amber-100 rounded-2xl text-[11px] text-amber-800 font-sans leading-relaxed">
        💡 **科研人员提示**：本平台采用 Python 后端引擎驱动 AI 计算任务，前端通过 REST API 与后端服务通信，支持多模型服务商无缝切换。
      </div>
    </div>
  );
}
