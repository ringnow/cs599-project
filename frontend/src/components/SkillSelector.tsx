/** 技能选择器 — 用于所有标签页选择执行技能 */
import React from "react";

interface SkillSelectorProps {
  skillOverride: string;
  onChange: (v: string) => void;
  allSkills: any[];
  label?: string;
  hint?: string;
}

export function SkillSelector({
  skillOverride, onChange, allSkills,
  label = "🛠️ 执行技能",
  hint = "选择特定技能覆盖默认的执行流程",
}: SkillSelectorProps) {
  return (
    <div className="border border-gray-200 rounded-2xl bg-white p-4 shadow-sm">
      <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">{label}</label>
      <select
        value={skillOverride}
        onChange={e => onChange(e.target.value)}
        className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      >
        <option value="">自动选择（推荐）</option>
        {allSkills.map((sk: any) => (
          <option key={sk.name} value={sk.name}>{sk.display_name || sk.name}</option>
        ))}
      </select>
      <p className="text-[9px] text-gray-400 mt-1">{hint}</p>
    </div>
  );
}
