/** 技能管理 Tab */
import React from "react";
import { Search, Activity, FileCode, Layers, ChevronUp, ChevronDown, Check } from "lucide-react";

interface Props {
  skills: any[];
  rawSkills: any[];
  installCode: string;
  setInstallCode: (v: string) => void;
  installFilename: string;
  setInstallFilename: (v: string) => void;
  isInstallExpanded: boolean;
  setIsInstallExpanded: (v: boolean) => void;
  setSkills: (fn: (prev: any[]) => any[]) => void;
  showToast: (msg: string) => void;
  fetchSkills: () => void;
  installSkill: () => void;
  uninstallSkill: (name: string) => void;
}

export function SkillsTab(props: Props) {
  const {
    skills, rawSkills, installCode, setInstallCode,
    installFilename, setInstallFilename,
    isInstallExpanded, setIsInstallExpanded,
    setSkills, showToast, fetchSkills,
    installSkill, uninstallSkill,
  } = props;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">技能管理 🔬</h2>
        <p className="text-xs text-gray-500 leading-relaxed font-sans">
          启用的模块将在每次生成时自动注入编译流水线中。支持安装自定义技能。
        </p>
      </div>

      <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm">
        <button onClick={() => setIsInstallExpanded(!isInstallExpanded)} className="w-full flex items-center justify-between text-xs font-bold text-gray-800">
          <span>➕ 安装新技能</span>
          {isInstallExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {isInstallExpanded && (
          <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
            <div>
              <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">文件名</label>
              <input value={installFilename} onChange={e => setInstallFilename(e.target.value)} className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
            </div>
            <div>
              <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">Python 技能代码</label>
              <textarea value={installCode} onChange={e => setInstallCode(e.target.value)} rows={6} placeholder="from src.skills.base import BaseSkill, SkillResult, SkillContext&#10;class MySkill(BaseSkill):&#10;    name = 'my_skill'&#10;    ..." className="w-full text-[11px] p-3 border rounded-xl bg-slate-50/50 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed" />
            </div>
            <button onClick={installSkill} className="w-full py-2.5 rounded-full text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 shadow-sm transition-all">安装</button>

            <div className="border-t border-gray-100 pt-3">
              <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-2">📁 上传 .py 或 .zip 技能文件</label>
              <input type="file" accept=".py,.zip" onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const formData = new FormData();
                formData.append("file", file);
                const ext = file.name.split('.').pop()?.toLowerCase();
                const endpoint = ext === 'zip' ? '/api/skills/install-zip' : '/api/skills/install-file';
                try {
                  const res = await fetch(endpoint, { method: 'POST', body: formData });
                  if (res.ok) { showToast(`技能 ${file.name} 安装成功`); fetchSkills(); }
                  else { const d = await res.json(); showToast(`安装失败: ${d.detail || '未知错误'}`); }
                } catch (_) { showToast('上传失败'); }
                e.target.value = '';
              }} className="w-full text-xs p-2 border rounded-xl bg-slate-50/50 file:mr-3 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" />
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {rawSkills.length > 0 && (
          <div className="text-[10px] text-gray-400 font-medium">共 {rawSkills.length} 个技能</div>
        )}
        {skills.map((sk, idx) => {
          const raw = rawSkills[idx] || {};
          const isUser = raw.is_user_skill;
          const tag = raw.tags?.[0] || sk.category;
          return (
            <div key={sk.id} className={`p-4 border rounded-2xl transition-all bg-white ${sk.isActive ? 'border-indigo-200 shadow-sm shadow-indigo-100/30' : 'border-gray-200'}`}>
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-xl mt-0.5 shrink-0 select-none ${sk.isActive ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500'}`}>
                  {sk.category === "检索" && <Search className="w-3.5 h-3.5" />}
                  {sk.category === "分析" && <Activity className="w-3.5 h-3.5" />}
                  {sk.category === "写作" && <FileCode className="w-3.5 h-3.5" />}
                  {sk.category === "辅助" && <Layers className="w-3.5 h-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-gray-800 font-sans">{sk.name}</span>
                    <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full select-none ${sk.category === "分析" ? "bg-amber-50 text-amber-700 border border-amber-100" : sk.category === "检索" ? "bg-blue-50 text-blue-700 border border-blue-100" : "bg-teal-50 text-teal-700 border border-teal-100"}`}>{tag}</span>
                    {isUser && <span className="text-[9px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-100">用户</span>}
                    {raw.version && <span className="text-[9px] text-gray-400">v{raw.version}</span>}
                  </div>
                  <p className="text-[10px] text-gray-400 font-sans leading-relaxed">{sk.description}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div onClick={() => setSkills((prev: any[]) => prev.map((item: any) => item.id === sk.id ? { ...item, isActive: !item.isActive } : item))} className={`w-5 h-5 rounded-md border flex items-center justify-center cursor-pointer select-none transition-all ${sk.isActive ? 'bg-indigo-600 border-indigo-500 text-white' : 'border-gray-300 bg-white'}`}>
                    {sk.isActive && <Check className="w-3.5 h-3.5 stroke-[3px]" />}
                  </div>
                  {isUser && (
                    <button onClick={() => uninstallSkill(raw.name)} className="text-[10px] text-rose-500 hover:bg-rose-50 px-2 py-1 rounded border border-rose-100">🗑️</button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
