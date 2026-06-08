/** 上下文拖拽上传面板 */
import React, { useState } from "react";
import { Layers, ChevronUp, ChevronDown, Upload, X } from "lucide-react";

interface ContextAccordionProps {
  expanded: boolean;
  setExpanded: (v: boolean) => void;
  context: string;
  setContext: (v: string) => void;
  files: Array<{ name: string; size: string; content: string }>;
  setFiles: (fn: (prev: any[]) => any[]) => void;
  removeFile: (idx: number) => void;
  historyId: string;
  setHistoryId: (v: string) => void;
  historyReports?: any[];
  onLoadHistory?: (id: string, setContext: any) => void;
}

export function ContextAccordion({
  expanded, setExpanded, context, setContext,
  files, setFiles, removeFile,
  historyId, setHistoryId, historyReports = [], onLoadHistory,
}: ContextAccordionProps) {
  const TEXT_EXTS = ['.txt', '.md', '.py', '.json', '.csv', '.js', '.ts', '.xml', '.yaml', '.yml', '.log', '.html', '.css'];

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!TEXT_EXTS.includes(ext)) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string || "";
        setFiles((prev: any) => [...prev, { name: file.name, size: (file.size / 1024).toFixed(1) + " KB", content: text }]);
        setContext((prev: string) => prev + `\n\n[文献附加内容 - ${file.name}]:\n${text}`);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="border border-gray-200 rounded-2xl bg-white shadow-sm overflow-hidden transition-all">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-4 text-xs font-semibold text-gray-700 hover:bg-slate-50/50 transition-colors bg-slate-50/30"
      >
        <div className="flex items-center gap-2 text-indigo-600">
          <Layers className="w-4 h-4" />
          <span>补充上下文</span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>
      {expanded && (
        <div className="p-5 border-t border-gray-100 space-y-4">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="border-2 border-dashed border-gray-200 hover:border-indigo-400 bg-slate-50/20 hover:bg-slate-50/70 p-5 rounded-xl text-center cursor-pointer transition-all relative group"
          >
            <Upload className="w-6 h-6 text-gray-400 mx-auto mb-2 group-hover:scale-110 group-hover:text-indigo-500 transition-transform" />
            <span className="block text-[11px] font-semibold text-gray-700 mb-1">拖入文件作为上下文</span>
            <span className="block text-[10px] text-gray-400">支持 .txt .md .py .json .csv 等文本文件</span>
          </div>
          {files.length > 0 && (
            <div className="space-y-1.5">
              {files.map((file, fIdx) => (
                <div key={fIdx} className="flex items-center justify-between bg-slate-50 border p-2 rounded-lg text-[10px] text-gray-600 font-mono">
                  <span className="truncate max-w-[200px]" title={file.name}>{file.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">{file.size}</span>
                    <button onClick={() => removeFile(fIdx)} className="p-0.5 rounded hover:bg-gray-200 text-rose-500"><X className="w-3 h-3" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {historyReports.length > 0 && (
            <div className="bg-slate-50/50 border border-gray-100 rounded-xl p-3">
              <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">选择历史记录作为上下文</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={historyId} onChange={e => setHistoryId(e.target.value)} className="min-w-0 flex-1 text-[11px] p-2 border rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500">
                  <option value="">-- 选择 --</option>
                  {historyReports.map((h: any) => (
                    <option key={h.id} value={h.id}>[{h.mode}] {h.display_name}</option>
                  ))}
                </select>
                {onLoadHistory && (
                  <button onClick={() => onLoadHistory(historyId, setContext)} className="whitespace-nowrap shrink-0 text-[10px] font-semibold text-white bg-indigo-600 border border-indigo-500 px-4 py-2 rounded-lg hover:bg-indigo-700">加载</button>
                )}
              </div>
            </div>
          )}
          <div>
            <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">追加学术资料：</label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="在此处输入额外的文献引用、数据序列..."
              className="w-full h-24 text-xs p-3 border rounded-xl bg-slate-50/55 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans leading-relaxed"
            />
          </div>
        </div>
      )}
    </div>
  );
}
