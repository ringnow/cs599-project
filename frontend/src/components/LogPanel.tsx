/** 日志/步骤展示面板 */
import React from "react";

interface LogPanelProps {
  progressLogs: string[];
  executionSteps: any[];
  logBoxEndRef: React.RefObject<HTMLDivElement | null>;
}

export function LogPanel({ progressLogs, executionSteps, logBoxEndRef }: LogPanelProps) {
  return (
    <div className="bg-[#1E293B] text-slate-300 p-4 rounded-xl max-h-52 overflow-y-auto font-mono text-[10px] leading-relaxed shadow-inner space-y-1 border border-slate-700/50">
      <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-2 flex items-center gap-2">
        <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse"></span>
        <span>控制台计算进程日志</span>
      </div>
      {progressLogs.map((log, idx) => (
        <div key={idx} className={`${log.startsWith("❌") || log.startsWith("🔴") ? "text-rose-400" : log.startsWith("✅") ? "text-emerald-400" : log.startsWith("⚠️") ? "text-amber-400" : log.startsWith("📡") || log.startsWith("📊") || log.startsWith("⏳") ? "text-cyan-300" : log.startsWith("💡") || log.startsWith("📍") ? "text-slate-500" : ""}`}>
          <span className="text-slate-600 mr-2 select-none">{'>'}</span>
          {log}
        </div>
      ))}
      {executionSteps.length > 0 && (
        <div className="border-t border-slate-700/50 pt-2 mt-2">
          <div className="text-[9px] uppercase tracking-widest text-slate-500 font-semibold mb-1">执行步骤</div>
          {executionSteps.map((step, idx) => {
            const icon = { done: "✅", running: "⏳", error: "❌", warning: "⚠️" }[step.status] || "➖";
            return (
              <div key={idx} className="text-slate-400">
                <span className="text-slate-600 mr-2 select-none">{'>'}</span>
                {icon} [{step.action}] {step.query || step.action} {step.result ? `→ ${step.result}` : ''}
              </div>
            );
          })}
        </div>
      )}
      <div ref={logBoxEndRef} />
    </div>
  );
}