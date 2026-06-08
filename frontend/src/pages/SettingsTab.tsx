/** 系统设置 Tab */
import React from "react";

interface Props {
  latexEnabled: boolean;
  setLatexEnabled: (v: boolean) => void;
  persistEnabled: boolean;
  setPersistEnabled: (v: boolean) => void;
}

export function SettingsTab({ latexEnabled, setLatexEnabled, persistEnabled, setPersistEnabled }: Props) {
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
      <div className="p-4 bg-amber-50 border border-amber-100 rounded-2xl text-[11px] text-amber-800 font-sans leading-relaxed">
        💡 **科研人员提示**：本平台采用 Python 后端引擎驱动 AI 计算任务，前端通过 REST API 与后端服务通信，支持多模型服务商无缝切换。
      </div>
    </div>
  );
}
