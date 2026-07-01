import { useState, useEffect, useRef, useMemo } from "react";
import { Clock, TrendingUp, Search, FileText, Filter, BookOpen, MessageSquare } from "lucide-react";

interface SearchHistoryItem {
  id: number | string;
  topic: string;
  num_sources: number;
  num_papers_cited: number;
  report_preview: string;
  duration_seconds: number;
  provider: string;
  model: string;
  created_at: string | null;
  /** 来源：'search_history' (SQL) 或 'report' (文件系统) */
  _source: string;
  /** 技能类型（报告/论文/综述等） */
  _mode: string;
}

interface ReportItem {
  id: string;
  mode: string;
  topic: string;
  display_name: string;
  time: string;
  content: string;
}

interface Stats {
  total_searches: number;
  avg_duration_seconds: number;
  avg_papers_cited: number;
  total_papers_cited: number;
}

const POLL_INTERVAL_MS = 15000;

const MODE_LABELS: Record<string, string> = {
  assistant: "智能助手",
  report: "研究报告",
  outline: "大纲生成",
  thesis: "学术论文",
  review: "综述写作",
  agents: "多智能体协作",
  research: "Deep Research",
  paper_writing: "学术论文",
  survey_writing: "综述写作",
  code_review: "代码审查",
  literature_review: "文献综述",
  office_export: "文档导出",
  ablation_study: "消融实验",
  data_preprocess: "数据预处理",
  review_quality: "质量评估",
};

export function SearchHistoryTab() {
  const [items, setItems] = useState<SearchHistoryItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [modeFilter, setModeFilter] = useState<string>("all");
  const fetchDataRef = useRef<() => void>(() => {});

  // Get unique modes from items for filter dropdown
  const availableModes = useMemo(() => {
    const modes = new Set<string>();
    items.forEach(item => { if (item._mode) modes.add(item._mode); });
    return Array.from(modes).sort();
  }, [items]);

  // Filter items by search query and mode
  const filteredItems = useMemo(() => {
    let result = items;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(item =>
        item.topic.toLowerCase().includes(q) ||
        (item.report_preview && item.report_preview.toLowerCase().includes(q))
      );
    }
    if (modeFilter !== "all") {
      result = result.filter(item => item._mode === modeFilter);
    }
    return result;
  }, [items, searchQuery, modeFilter]);

  const fetchData = async () => {
    try {
      setError(null);
      const token = localStorage.getItem("cs599_token") || "";
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [sqlRes, reportRes, statsRes] = await Promise.all([
        fetch("/api/search-history", { headers }),
        fetch("/api/history", { headers }),
        fetch("/api/search-history/stats", { headers }),
      ]);

      const merged: SearchHistoryItem[] = [];

      // 1. Load from SQL search_history
      if (sqlRes.ok) {
        const d = await sqlRes.json();
        (d.items || []).forEach((item: any) => {
          merged.push({
            id: `sql_${item.id}`,
            topic: item.topic || "未命名",
            num_sources: item.num_sources || 0,
            num_papers_cited: item.num_papers_cited || 0,
            report_preview: item.report_preview || "",
            duration_seconds: item.duration_seconds || 0,
            provider: item.provider || "",
            model: item.model || "",
            created_at: item.created_at || null,
            _source: "search_history",
            _mode: "research",
          });
        });
      }

      // 2. Load from file-based reports (have full content)
      if (reportRes.ok) {
        const reports: ReportItem[] = await reportRes.json();
        reports.forEach((r) => {
          // Deduplicate by topic + time
          const dup = merged.some(m =>
            m.topic === r.topic && m.created_at?.includes(r.time)
          );
          if (!dup) {
            merged.push({
              id: `rpt_${r.id}`,
              topic: r.display_name || r.topic || "未命名",
              num_sources: 0,
              num_papers_cited: 0,
              report_preview: (r.content || "").slice(0, 500),
              duration_seconds: 0,
              provider: "",
              model: "",
              created_at: r.time ? new Date(r.time).toISOString() : null,
              _source: "report",
              _mode: r.mode || "assistant",
            });
          }
        });
      }

      // 3. Sort by time descending (newest first)
      merged.sort((a, b) => {
        const tA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const tB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return tB - tA;
      });

      setItems(merged);

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (e: any) {
      setError(e.message || "网络错误，无法加载搜索历史");
    } finally {
      setLoading(false);
    }
  };
  fetchDataRef.current = fetchData;

  useEffect(() => {
    fetchDataRef.current();
    let interval: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      if (interval) return;
      interval = setInterval(() => fetchDataRef.current(), POLL_INTERVAL_MS);
    };
    const stop = () => {
      if (interval) { clearInterval(interval); interval = null; }
    };
    const onVisibility = () => { document.hidden ? stop() : start(); };
    start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const formatTime = (s: number) => (s < 60 ? `${s.toFixed(1)}s` : `${(s / 60).toFixed(1)}m`);
  const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleString("zh-CN") : "-";

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-6 pb-3 flex items-center justify-between border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-xl text-indigo-600">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">历史记录</h2>
            <p className="text-xs text-slate-400">所有任务的历史记录与统计</p>
          </div>
        </div>
        <button
          onClick={fetchData}
          className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition"
        >
          刷新
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="px-6 py-3 border-b border-slate-100 shrink-0 space-y-2">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索历史记录关键词..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50
              focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
          />
        </div>
        {availableModes.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <button
              onClick={() => setModeFilter("all")}
              className={`text-xs px-2.5 py-1 rounded-full transition ${
                modeFilter === "all"
                  ? "bg-indigo-100 text-indigo-700 font-medium"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              全部
            </button>
            {availableModes.map((mode) => (
              <button
                key={mode}
                onClick={() => setModeFilter(mode)}
                className={`text-xs px-2.5 py-1 rounded-full transition ${
                  modeFilter === mode
                    ? "bg-indigo-100 text-indigo-700 font-medium"
                    : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                }`}
              >
                {MODE_LABELS[mode] || mode}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mt-3 p-2.5 rounded-lg bg-red-50 text-red-600 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchData} className="underline hover:text-red-700">重试</button>
        </div>
      )}

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 px-6 py-3 border-b border-slate-100 shrink-0">
          <StatCard icon={<Search className="w-4 h-4" />} label="搜索次数" value={stats.total_searches} />
          <StatCard icon={<Clock className="w-4 h-4" />} label="平均耗时" value={formatTime(stats.avg_duration_seconds)} />
          <StatCard icon={<FileText className="w-4 h-4" />} label="平均引用" value={stats.avg_papers_cited.toFixed(1)} />
          <StatCard icon={<TrendingUp className="w-4 h-4" />} label="总引用数" value={stats.total_papers_cited} />
        </div>
      )}

      {/* Count indicator */}
      {!loading && (
        <div className="px-6 py-2 text-xs text-slate-400 border-b border-slate-50 shrink-0">
          {filteredItems.length === 0
            ? searchQuery
              ? "未找到匹配的记录"
              : "暂无历史记录"
            : `共 ${filteredItems.length} 条记录${searchQuery ? ` (关键词: "${searchQuery}")` : ""}`
          }
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-slate-400 text-sm">
            加载中...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
            <BookOpen className="w-10 h-10 text-slate-300" />
            <p className="text-sm">暂无历史记录</p>
            <p className="text-xs">运行任务后结果将自动保存到这里</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="px-6 py-3 hover:bg-slate-50 transition cursor-pointer"
                onClick={() => setExpanded(expanded === item.id ? null : item.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{item.topic}</p>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600">
                        {MODE_LABELS[item._mode] || item._mode}
                      </span>
                      {item._source === "report" && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600">含全文</span>
                      )}
                      <span className="text-xs text-slate-400">{item.num_sources} 来源</span>
                      <span className="text-xs text-slate-400">{item.num_papers_cited} 引用</span>
                      {item.duration_seconds > 0 && (
                        <span className="text-xs text-slate-400">{formatTime(item.duration_seconds)}</span>
                      )}
                      {item.provider && (
                        <span className="text-xs text-slate-300">{item.provider}/{item.model}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-slate-300 whitespace-nowrap">{formatDate(item.created_at)}</span>
                </div>
                {expanded === item.id && item.report_preview && (
                  <div className="mt-2 p-3 bg-slate-50 rounded-lg text-xs text-slate-600 max-h-40 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                    {item.report_preview}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
      <div className="flex items-center gap-1.5 text-slate-400 mb-1">
        {icon}
        <span className="text-[10px] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-lg font-bold text-slate-700">{value}</p>
    </div>
  );
}
