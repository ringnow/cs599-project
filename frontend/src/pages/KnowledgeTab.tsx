/** 知识库管理 Tab — RAG 文档上传 / 检索 / 管理 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import { BookOpen, Upload, Search, Trash2, FileText, AlertCircle, CheckCircle, MessageSquare, Send } from "lucide-react";
import { apiFetch } from "../utils/api";

/** Extract a human-readable error message from a FastAPI response.
 *  FastAPI validation errors return detail as an array of objects,
 *  which String() would turn into "[object Object]". */
function extractError(data: any): string {
  if (!data) return "Unknown error";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((e: any) => e.msg || JSON.stringify(e)).join("; ");
  }
  if (typeof data === "string") return data;
  return JSON.stringify(data);
}

interface Document {
  doc_id: string;
  title: string;
  source: string;
  type: string;
  username: string;
  created_at: string;
}

interface SearchResult {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, any>;
}

export function KnowledgeTab() {
  const [stats, setStats] = useState<any>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qaQuestion, setQaQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState("");
  const [qaSources, setQaSources] = useState<any[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [statsRes, docsRes] = await Promise.all([
        apiFetch("/api/knowledge/stats"),
        apiFetch("/api/knowledge/documents"),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (docsRes.ok) {
        const data = await docsRes.json();
        setDocuments(data.documents || []);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load knowledge base");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiFetch("/api/knowledge/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(extractError(data));
      setUploadMsg({ ok: true, text: `✓ ${data.message} (${data.chunks_added} chunks)` });
      refresh();
    } catch (e: any) {
      setUploadMsg({ ok: false, text: `✗ ${e.message || "Upload failed"}` });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    try {
      const res = await apiFetch(`/api/knowledge/documents/${docId}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(extractError(data));
      }
      refresh();
    } catch (e: any) {
      setError(e.message || "Delete failed");
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const res = await apiFetch(
        `/api/knowledge/search?q=${encodeURIComponent(searchQuery)}&top_k=5`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(extractError(data));
      setSearchResults(data.results || []);
    } catch (e: any) {
      setError(e.message || "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleQaAsk = async () => {
    if (!qaQuestion.trim()) return;
    setQaLoading(true);
    setQaAnswer("");
    setQaSources([]);
    setError(null);
    try {
      const res = await apiFetch("/api/knowledge/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: qaQuestion, top_k: 5 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(extractError(data));
      setQaAnswer(data.answer || "");
      setQaSources(data.sources || []);
    } catch (e: any) {
      setError(e.message || "QA request failed");
    } finally {
      setQaLoading(false);
    }
  };

  const ragEnabled = stats?.enabled && stats?.embedder_available;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <BookOpen className="w-6 h-6 text-emerald-500" />
        <h2 className="text-xl font-semibold">知识库 (RAG)</h2>
      </div>

      {!ragEnabled && (
        <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            <p className="font-medium">RAG 未启用</p>
            <p className="mt-1">
              需要 <code className="px-1 bg-amber-100 rounded">chromadb</code> 和{" "}
              <code className="px-1 bg-amber-100 rounded">sentence-transformers</code>。
              运行: <code className="px-1 bg-amber-100 rounded">pip install chromadb sentence-transformers PyMuPDF</code>
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="总文档数" value={stats?.total_documents ?? 0} icon={<FileText className="w-5 h-5 text-blue-500" />} />
        <StatCard label="总块数" value={stats?.total_chunks ?? 0} icon={<BookOpen className="w-5 h-5 text-emerald-500" />} />
        <StatCard label="状态" value={ragEnabled ? "已启用" : "未启用"} icon={ragEnabled ? <CheckCircle className="w-5 h-5 text-emerald-500" /> : <AlertCircle className="w-5 h-5 text-amber-500" />} />
      </div>

      {/* Upload Section */}
      <div className="p-5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Upload className="w-4 h-4" /> 上传文档
        </h3>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleUpload}
          disabled={uploading || !ragEnabled}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0
            file:text-sm file:font-medium file:bg-emerald-50 file:text-emerald-700
            hover:file:bg-emerald-100 disabled:opacity-50"
        />
        <p className="mt-2 text-xs text-gray-400">支持 PDF / TXT / MD，最大 10MB</p>
        {uploading && <p className="mt-2 text-sm text-blue-500">上传中...</p>}
        {uploadMsg && (
          <p className={`mt-2 text-sm ${uploadMsg.ok ? "text-emerald-600" : "text-red-600"}`}>
            {uploadMsg.text}
          </p>
        )}
      </div>

      {/* Search Section */}
      <div className="p-5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Search className="w-4 h-4" /> 语义检索测试
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入查询，测试本地知识库检索..."
            disabled={!ragEnabled}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-transparent
              focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !ragEnabled || !searchQuery.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-md
              hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {searching ? "搜索中..." : "搜索"}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            {searchResults.map((r, i) => (
              <div key={i} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-500">来源: {r.metadata?.source || "unknown"}</span>
                  <span className="text-xs font-mono text-emerald-600">score: {r.score}</span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">{r.text}</p>
              </div>
            ))}
          </div>
        )}
        {searchResults.length === 0 && searchQuery && !searching && (
          <p className="mt-3 text-sm text-gray-400">无结果</p>
        )}
      </div>

      {/* RAG Q&A Section */}
      <div className="p-5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-indigo-500" /> 知识库问答
        </h3>
        <p className="text-xs text-gray-400 mb-3">基于知识库内容，使用 AI 模型生成回答</p>
        <div className="flex gap-2">
          <input
            type="text"
            value={qaQuestion}
            onChange={(e) => setQaQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !qaLoading && handleQaAsk()}
            placeholder="输入问题，AI 将基于知识库回答..."
            disabled={!ragEnabled || qaLoading}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-transparent
              focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
          />
          <button
            onClick={handleQaAsk}
            disabled={qaLoading || !ragEnabled || !qaQuestion.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md
              hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {qaLoading ? (
              <>思考中...</>
            ) : (
              <><Send className="w-3.5 h-3.5" /> 提问</>
            )}
          </button>
        </div>
        {qaAnswer && (
          <div className="mt-4 space-y-3">
            <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-md border border-indigo-100 dark:border-indigo-800">
              <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">{qaAnswer}</p>
            </div>
            {qaSources.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">来源 ({qaSources.length})</p>
                <div className="space-y-1.5">
                  {qaSources.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-500">
                      <span className="text-indigo-400 font-mono flex-shrink-0">{s.score?.toFixed(2)}</span>
                      <span className="line-clamp-1">{s.source}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {qaLoading && (
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-400">
            <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            正在检索知识库并生成回答...
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="p-5 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4" /> 文档列表 ({documents.length})
          </h3>
          <button onClick={refresh} className="text-xs text-emerald-600 hover:underline">
            刷新
          </button>
        </div>
        {documents.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">
            知识库为空。上传文档或运行研究任务后会自动入库。
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.doc_id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-md"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{doc.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {doc.type} · {doc.doc_id}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(doc.doc_id)}
                  className="ml-3 p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  title="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: any; icon: React.ReactNode }) {
  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}
