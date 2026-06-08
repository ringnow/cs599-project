/** Markdown 渲染器 — 支持中文学术 Markdown 格式的轻量级渲染 */
import React from "react";

export function MarkdownRenderer({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split("\n");
  let insideCodeBlock = false;
  let codeBlockLines: string[] = [];
  let insideTable = false;
  let tableHeadings: string[] = [];
  let tableRows: string[][] = [];
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      if (insideCodeBlock) {
        insideCodeBlock = false;
        const codeText = codeBlockLines.join("\n");
        elements.push(
          <div key={`code-${i}`} className="my-3 font-mono text-xs overflow-x-auto bg-[#1E293B] text-slate-100 p-4 border-l-4 border-cyan-500 rounded-r-xl shadow-inner relative group">
            <div className="absolute top-2 right-2 text-[10px] uppercase bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-sans select-none opacity-0 group-hover:opacity-100 transition-opacity">代码片段</div>
            <pre>{codeText}</pre>
          </div>
        );
        codeBlockLines = [];
      } else {
        insideCodeBlock = true;
      }
      continue;
    }

    if (insideCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Tables
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      const columns = line.split("|").slice(1, -1).map(col => col.trim());
      if (columns.every(col => col === "" || col.startsWith("---") || col.startsWith(":-") || col.startsWith("-:"))) continue;
      if (!insideTable) {
        insideTable = true;
        tableHeadings = columns;
        tableRows = [];
      } else {
        tableRows.push(columns);
      }
      continue;
    } else if (insideTable) {
      insideTable = false;
      elements.push(
        <div key={`table-${i}`} className="my-4 overflow-x-auto border border-gray-200 rounded-xl bg-white shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {tableHeadings.map((head, hIdx) => <th key={`h-${hIdx}`} className="py-3 px-4 font-semibold text-gray-700">{head}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tableRows.map((row, rIdx) => (
                <tr key={`r-${rIdx}`} className="hover:bg-slate-50/55 transition-colors">
                  {row.map((val, cIdx) => <td key={`c-${cIdx}`} className="py-2.5 px-4 text-gray-600 font-sans leading-relaxed">{val}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Headings
    if (line.startsWith("### ")) {
      elements.push(<h3 key={i} className="text-sm font-semibold text-gray-800 mt-6 mb-3 flex items-center gap-2 border-b border-gray-100 pb-1.5 font-sans tracking-wide"><span className="w-1.5 h-4 bg-indigo-500 rounded-sm inline-block"></span>{line.replace("### ", "")}</h3>);
    } else if (line.startsWith("#### ")) {
      elements.push(<h4 key={i} className="text-xs font-semibold text-gray-700 mt-4 mb-2 font-sans tracking-wide">{line.replace("#### ", "")}</h4>);
    } else if (line.startsWith("## ")) {
      elements.push(<h2 key={i} className="text-base font-bold text-gray-900 mt-8 mb-4 border-b pb-2 font-sans tracking-wide">{line.replace("## ", "")}</h2>);
    } else if (line.startsWith("# ")) {
      elements.push(<h1 key={i} className="text-lg font-bold text-gray-950 mt-10 mb-6 font-sans tracking-tight">{line.replace("# ", "")}</h1>);
    }
    // Lists
    else if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(<li key={i} className="ml-5 list-disc text-xs text-gray-600 leading-relaxed my-1.5 font-sans">{line.substring(2)}</li>);
    }
    else if (/^\d+\.\s/.test(line)) {
      const dotIdx = line.indexOf(". ");
      elements.push(<div key={i} className="ml-4 flex gap-2 items-start text-xs text-gray-600 leading-relaxed my-1.5 font-sans"><span className="font-semibold text-indigo-500 min-w-4 select-none">{line.substring(0, dotIdx + 1)}</span><span>{line.substring(dotIdx + 2)}</span></div>);
    }
    // Quotes
    else if (line.startsWith("> ")) {
      elements.push(<blockquote key={i} className="pl-4 border-l-4 border-indigo-400 bg-indigo-50/40 py-2 my-3 rounded-r-xl text-xs text-indigo-900 font-sans italic leading-relaxed">{line.replace("> ", "")}</blockquote>);
    }
    // Empty
    else if (line.trim() === "") {
      continue;
    }
    // Paragraphs
    else {
      elements.push(<p key={i} className="text-xs text-gray-600 leading-relaxed font-sans my-2.5">{line}</p>);
    }
  }

  return <div className="space-y-1">{elements}</div>;
}
