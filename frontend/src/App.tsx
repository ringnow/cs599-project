/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Brain,
  Cpu,
  Layers,
  Search,
  FileText,
  Settings,
  Trash2,
  Play,
  Square,
  Activity,
  CheckCircle2,
  Network,
  ChevronDown,
  ChevronUp,
  Upload,
  X,
  Sparkles,
  Plus,
  Server,
  Check,
  FileCode,
  BookOpen,
  Sliders,
  HelpCircle
} from "lucide-react";
import { Tab, HistoryItem, SkillItem } from "./types";

export default function App() {
  // Navigation & Base States
  const [activeTab, setActiveTab] = useState<Tab>("assistant");
  const [apiUrl, setApiUrl] = useState<string>(() => {
    return localStorage.getItem("cs599_api_url") || "";
  });
  const [apiKey, setApiKey] = useState<string>(() => {
    return localStorage.getItem("cs599_api_key") || "";
  });
  const [selectedModel, setSelectedModel] = useState<string>("gemini-3.5-flash");

  // History state
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Collapsible accordion for additional context
  const [isContextExpanded, setIsContextExpanded] = useState<boolean>(false);
  const [contextText, setContextText] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);

  // Per-tab context states
  const [reportContext, setReportContext] = useState<string>("");
  const [reportFiles, setReportFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);
  const [reportContextExpanded, setReportContextExpanded] = useState<boolean>(false);
  const [outlineContext, setOutlineContext] = useState<string>("");
  const [outlineFiles, setOutlineFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);
  const [outlineContextExpanded, setOutlineContextExpanded] = useState<boolean>(false);
  const [thesisContext, setThesisContext] = useState<string>("");
  const [thesisFiles, setThesisFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);
  const [thesisContextExpanded, setThesisContextExpanded] = useState<boolean>(false);
  const [reviewContext, setReviewContext] = useState<string>("");
  const [reviewFiles, setReviewFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);
  const [reviewContextExpanded, setReviewContextExpanded] = useState<boolean>(false);
  const [agentContext, setAgentContext] = useState<string>("");
  const [agentFiles, setAgentFiles] = useState<Array<{ name: string; size: string; content: string }>>([]);
  const [agentContextExpanded, setAgentContextExpanded] = useState<boolean>(false);

  // Per-tab history selector states
  const [reportHistoryId, setReportHistoryId] = useState<string>("");
  const [outlineHistoryId, setOutlineHistoryId] = useState<string>("");
  const [thesisHistoryId, setThesisHistoryId] = useState<string>("");
  const [reviewHistoryId, setReviewHistoryId] = useState<string>("");
  const [agentHistoryId, setAgentHistoryId] = useState<string>("");

  // Provider/Model selector state
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  // Model sniffing state
  const [sniffedModels, setSniffedModels] = useState<any[]>([]);

  // Custom provider add state
  const [customProviderName, setCustomProviderName] = useState<string>("");
  const [customProviderUrl, setCustomProviderUrl] = useState<string>("");
  const [customProviderKey, setCustomProviderKey] = useState<string>("");
  const [customProviderModel, setCustomProviderModel] = useState<string>("");
  const [showCustomProvider, setShowCustomProvider] = useState<boolean>(false);

  // Form states per Tab

  // 1. 智能助手
  const [assistantPrompt, setAssistantPrompt] = useState<string>(
    "帮助我研究多智能体协作的最新进展并写一份全面的总结。"
  );

  // 2. 研究报告
  const [reportSubject, setReportSubject] = useState<string>("多智能体混合强化学习收敛性分析");
  const [reportField, setReportField] = useState<string>("算网融合 / 理论决策控制");
  const [reportDepth, setReportDepth] = useState<"基础" | "详细" | "专家">("详细");
  const [includeCharts, setIncludeCharts] = useState<boolean>(true);
  const [referenceCount, setReferenceCount] = useState<number>(9);

  // 3. 大纲生成
  const [outlineSubject, setOutlineSubject] = useState<string>("大语言模型智能体博弈与线性化控制");
  const [outlineField, setOutlineField] = useState<string>("深度强化学习 / 自然语言处理");

  // 4. 学术论文
  const [thesisBlock, setThesisBlock] = useState<string>("第三章第一节：异步分布式节点损失界限证明");
  const [thesisPrompt, setThesisPrompt] = useState<string>("提供详实的极限值不等式推导，包含收敛定理的Lipschitz常数L约束");
  const [thesisStyle, setThesisStyle] = useState<string>("Nature标准格式");

  // 5. 综述写作
  const [reviewKeyword, setReviewKeyword] = useState<string>("Federated Multi-Agent Reinforcement Learning");
  const [reviewSourceCount, setReviewSourceCount] = useState<number>(12);

  // 6. 多智能体协作
  const [agentTopic, setAgentTopic] = useState<string>("基于自适应对齐的有向图智能体协作");
  const [agentExchanges, setAgentExchanges] = useState<Array<{ agent: string; message: string }>>([]);

  // Active generation results
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progressLogs, setProgressLogs] = useState<string[]>([]);
  const [currentMarkdown, setCurrentMarkdown] = useState<string>("");

  // Skills Manager states
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [rawSkills, setRawSkills] = useState<any[]>([]);
  const [installCode, setInstallCode] = useState("");
  const [installFilename, setInstallFilename] = useState("my_skill.py");
  const [isInstallExpanded, setIsInstallExpanded] = useState(false);

  // Providers / MCP / Search states
  const [providersList, setProvidersList] = useState<any[]>([]);
  const [providersHealth, setProvidersHealth] = useState<Record<string, {healthy: boolean, message?: string}>>({});
  const [presetsList, setPresetsList] = useState<any[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [tavilyRunning, setTavilyRunning] = useState(false);
  const [searchBackends, setSearchBackends] = useState<any[]>([]);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editApiKey, setEditApiKey] = useState("");
  const [addPresetName, setAddPresetName] = useState("");
  const [addCustomUrl, setAddCustomUrl] = useState("");
  const [addApiKey, setAddApiKey] = useState("");
  const [tavilyKey, setTavilyKey] = useState("");
  const [tavilyProxy, setTavilyProxy] = useState("http://localhost:7980");
  const [remoteMcpUrl, setRemoteMcpUrl] = useState("");
  const [remoteMcpKey, setRemoteMcpKey] = useState("");
  const [braveSearchKey, setBraveSearchKey] = useState("");
  const [bochaSearchKey, setBochaSearchKey] = useState("");
  const [semanticScholarKey, setSemanticScholarKey] = useState("");

  // Extra form params (Task 4)
  const [outlinePaperType, setOutlinePaperType] = useState<string>("研究论文");
  const [thesisPaperType, setThesisPaperType] = useState<string>("research");
  const [thesisLength, setThesisLength] = useState<string>("medium");
  const [reviewScope, setReviewScope] = useState<string>("focused");
  const [reviewTaxonomy, setReviewTaxonomy] = useState<boolean>(true);
  const [reviewComparisons, setReviewComparisons] = useState<boolean>(true);
  const [agentDocType, setAgentDocType] = useState<string>("report");
  const [agentIterations, setAgentIterations] = useState<number>(1);

  // Tool selector states (Task 5)
  const [allSkills, setAllSkills] = useState<any[]>([]);
  const [skillOverride, setSkillOverride] = useState<string>("");
  const [selectedMcpServers, setSelectedMcpServers] = useState<string[]>([]);

  // Context history selector (Task 3)
  const [historyReports, setHistoryReports] = useState<any[]>([]);

  // Settings Tab (Task 8C)
  const [latexEnabled, setLatexEnabled] = useState<boolean>(() => localStorage.getItem("cs599_latex") !== "false");
  const [persistEnabled, setPersistEnabled] = useState<boolean>(() => localStorage.getItem("cs599_persist") !== "false");

  // Notification success alert
  const [toastMessage, setToastMessage] = useState<string>("");

  // Refs for auto scrolling log box
  const logBoxEndRef = useRef<HTMLDivElement>(null);
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentRequestIdRef = useRef<string>("");

  const clearAllTimers = () => {
    timerRefs.current.forEach(clearTimeout);
    timerRefs.current = [];
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const addTimedLog = (msg: string, delay: number) => {
    const id = setTimeout(() => {
      setProgressLogs(prev => [...prev, msg]);
    }, delay);
    timerRefs.current.push(id);
  };

  useEffect(() => {
    if (logBoxEndRef.current) {
      logBoxEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [progressLogs]);

  // Fetch skills from backend API
  const fetchSkills = async () => {
    try {
      const res = await fetch("/api/skills");
      if (res.ok) {
        const data = await res.json();
        setRawSkills(Array.isArray(data) ? data : []);
        if (Array.isArray(data) && data.length > 0) {
          setSkills(data.map((s: any, i: number) => ({
            id: `sk_${s.name || i}`,
            name: s.display_name || s.name,
            description: s.description || "",
            category: (s.tags?.includes("检索") ? "检索" : s.tags?.includes("分析") ? "分析" : s.tags?.includes("写作") ? "写作" : "辅助") as "检索" | "分析" | "写作" | "辅助",
            isActive: true,
          })));
          return;
        }
      }
    } catch (_) {}
    // Fallback: hardcoded skills
    setRawSkills([]);
    setSkills(fallbackSkills);
  };
  const fetchHistoryReports = async () => {
    try {
      const r = await fetch("/api/history");
      if (r.ok) {
        const d = await r.json();
        if (Array.isArray(d)) {
          setHistoryReports(d);
          setHistory(d.map((h: any) => ({
            id: h.id,
            timestamp: h.time,
            type: h.mode === "report" ? "研究报告" :
                  h.mode === "outline" ? "大纲生成" :
                  h.mode === "thesis" ? "学术论文" :
                  h.mode === "review" ? "综述写作" :
                  h.mode === "agents" ? "多智能体协作" :
                  h.mode === "assistant" ? "智能助手" : h.mode,
            title: h.display_name || h.topic || "未命名任务",
            content: h.content || "",
          })));
        }
      }
    } catch (_) {}
  };
  const fetchAllSkills = async () => {
    try { const r = await fetch("/api/skills"); if (r.ok) { const d = await r.json(); if (Array.isArray(d)) setAllSkills(d); } } catch (_) {}
  };

  // Load skills & providers from backend API on mount
  useEffect(() => { fetchSkills(); fetchHistoryReports(); fetchAllSkills(); }, []);

  // Hardcoded fallback skills
  const fallbackSkills: SkillItem[] = [
    { id: "s1", name: "文献库快速清洗", description: "自动去重和清洗格式错误的 BibTex 图书馆条目", category: "检索", isActive: true },
    { id: "s2", name: "Latex 数学公式自动重构", description: "将粗糙公式表示归一化为标准的 AMS 符号排版规范", category: "辅助", isActive: true },
    { id: "s3", name: "消融实验矩阵拟合检测", description: "识别数据点中对于消融曲线突变存在异常的特征噪音", category: "分析", isActive: false },
    { id: "s4", name: "引用链自动交叉审计", description: "检索引用层级关系，智能指出文献论证自闭环套环的逻辑漏洞", category: "检索", isActive: false },
    { id: "s5", name: "学术语气一键降重与强化学术感", description: "将第一人称主观叙述一键平滑编译为严谨无瑕的第三人称被动语态", category: "写作", isActive: true },
    { id: "s6", name: "收敛性能数值拟合可视化", description: "解析日志中的 Loss 序列信息自动渲染生成对照趋势 Markdown 数据表", category: "分析", isActive: true },
  ];

  // Fetch providers, MCP servers, search backends from API
  const fetchProviders = async () => {
    try {
      const res = await fetch("/api/providers");
      if (res.ok) { const d = await res.json(); if (Array.isArray(d)) setProvidersList(d); }
    } catch (_) {}
  };
  const fetchPresets = async () => {
    try {
      const res = await fetch("/api/providers/presets");
      if (res.ok) { const d = await res.json(); setPresetsList(d.presets || []); }
    } catch (_) {}
  };
  const fetchMcpServers = async () => {
    try {
      const res = await fetch("/api/mcp/servers");
      if (res.ok) { const d = await res.json(); if (Array.isArray(d)) setMcpServers(d); }
    } catch (_) {}
  };
  const fetchTavilyStatus = async () => {
    try {
      const res = await fetch("/api/mcp/tavily/status");
      if (res.ok) { const d = await res.json(); setTavilyRunning(d.running); }
    } catch (_) {}
  };
  const fetchSearchBackends = async () => {
    try {
      const res = await fetch("/api/search-backends");
      if (res.ok) { const d = await res.json(); if (Array.isArray(d)) setSearchBackends(d); }
    } catch (_) {}
  };
  const fetchHealth = async () => {
    try { const r = await fetch("/api/health"); if (r.ok) { setBackendOnline(true); } else { setBackendOnline(false); } } catch (_) { setBackendOnline(false); }
    try { const r = await fetch("/api/providers/health"); if (r.ok) { const d = await r.json(); setProvidersHealth(d); } } catch (_) {}
  };
  const refreshAll = () => { fetchProviders(); fetchPresets(); fetchMcpServers(); fetchTavilyStatus(); fetchSearchBackends(); fetchHealth(); };

  // Load all data on mount
  useEffect(() => { refreshAll(); }, []);

  // Start editing a provider
  const startEdit = (p: any) => {
    setEditingProvider(p.name);
    setEditBaseUrl(p.base_url || "");
    setEditModel(p.default_model || "");
    setEditApiKey("");
  };

  // Save provider edits
  const saveEdit = async (name: string) => {
    await fetch(`/api/providers/${name}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({base_url: editBaseUrl, default_model: editModel}) });
    if (editApiKey) {
      await fetch(`/api/providers/${name}/key`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({api_key: editApiKey}) });
    }
    setEditingProvider(null);
    showToast(`服务商 ${name} 已更新`);
    fetchProviders();
  };

  // Delete provider
  const deleteProvider = async (name: string) => {
    await fetch(`/api/providers/${name}`, { method: "DELETE" });
    showToast(`服务商 ${name} 已删除`);
    fetchProviders();
  };

  // Sniff models from provider
  const sniffModels = async (name: string) => {
    try {
      const r = await fetch(`/api/providers/${name}/models`);
      if (r.ok) {
        const d = await r.json();
        const models = d.models || [];
        setSniffedModels(models);
        showToast(`发现 ${models.length} 个模型`);
        // Auto-set the first model as selected
        if (models.length > 0) {
          setSelectedModel(models[0].id);
        }
        fetchProviders();
      }
    } catch (_) { showToast("模型嗅探失败"); }
  };

  // Add provider from preset
  const addProvider = async () => {
    if (!addPresetName) { showToast("请选择预设"); return; }
    const res = await fetch("/api/providers", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({preset_name: addPresetName, api_key: addApiKey, custom_base_url: addCustomUrl || null}) });
    if (res.ok) { showToast(`服务商 ${addPresetName} 已添加`); setAddPresetName(""); setAddCustomUrl(""); setAddApiKey(""); fetchProviders(); }
    else { const e = await res.json(); showToast(`添加失败: ${e.detail}`); }
  };

  // Add custom provider
  const addCustomProviderFn = async () => {
    if (!customProviderName || !customProviderUrl) { showToast("名称和 Base URL 不能为空"); return; }
    const res = await fetch("/api/providers/custom", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({name: customProviderName, base_url: customProviderUrl, api_key: customProviderKey, default_model: customProviderModel}) });
    if (res.ok) {
      showToast(`自定义服务商已添加`);
      setCustomProviderName(""); setCustomProviderUrl(""); setCustomProviderKey(""); setCustomProviderModel("");
      setAddPresetName(""); setShowCustomProvider(false);
      fetchProviders();
    } else { const e = await res.json(); showToast(`添加失败: ${e.detail}`); }
  };

  // Tavily actions
  const startTavily = async () => {
    const res = await fetch("/api/mcp/tavily/start", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({api_key: tavilyKey, proxy: tavilyProxy}) });
    if (res.ok) { showToast("Tavily MCP 已启动"); fetchTavilyStatus(); fetchMcpServers(); }
    else { const e = await res.json(); showToast(`启动失败: ${e.detail}`); }
  };
  const stopTavily = async () => {
    await fetch("/api/mcp/tavily/stop", { method: "POST" });
    showToast("Tavily MCP 已停止"); fetchTavilyStatus(); fetchMcpServers();
  };

  // Add remote MCP
  const addRemoteMcp = async () => {
    if (!remoteMcpUrl.trim()) { showToast("请输入 MCP URL"); return; }
    const name = remoteMcpUrl.trim().split("//").pop()?.split("/")[0].replace(/\./g, "_") || "remote_mcp";
    const res = await fetch("/api/mcp/servers", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({name, display_name: `远程 ${name}`, url: remoteMcpUrl.trim(), api_key: remoteMcpKey, tools_prefix: "tavily_"}) });
    if (res.ok) { showToast("远程 MCP 已添加"); setRemoteMcpUrl(""); setRemoteMcpKey(""); fetchMcpServers(); }
    else { const e = await res.json(); showToast(`添加失败: ${e.detail}`); }
  };

  // Toggle / delete MCP
  const toggleMcp = async (name: string) => {
    try { await fetch(`/api/mcp/servers/${name}/toggle`, { method: "POST" }); fetchMcpServers(); } catch (_) {}
  };
  const deleteMcp = async (name: string) => {
    await fetch(`/api/mcp/servers/${name}`, { method: "DELETE" });
    showToast("MCP 已删除"); fetchMcpServers();
  };

  // Install / uninstall skill
  const installSkill = async () => {
    if (!installCode.trim()) { showToast("请粘贴技能代码"); return; }
    const res = await fetch("/api/skills/install", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({code: installCode, filename: installFilename}) });
    if (res.ok) { showToast("技能安装成功"); setInstallCode(""); fetchSkills(); }
    else { const e = await res.json(); showToast(`安装失败: ${e.detail || JSON.stringify(e)}`); }
  };
  const uninstallSkill = async (name: string) => {
    const res = await fetch(`/api/skills/${name}`, { method: "DELETE" });
    if (res.ok) { showToast(`技能 ${name} 已卸载`); fetchSkills(); }
    else { const e = await res.json(); showToast(`卸载失败: ${e.detail || JSON.stringify(e)}`); }
  };

  // Save search API key
  const saveSearchKey = async (name: string, key: string) => {
    await fetch("/api/search-keys", { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify({name, api_key: key}) });
    showToast(`${name} 搜索 Key 已保存`);
  };

  // Save Back-end settings to localStorage
  const handleSaveApiSettings = () => {
    localStorage.setItem("cs599_api_url", apiUrl);
    localStorage.setItem("cs599_api_key", apiKey);
    showToast("服务商配置保存成功");
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage("");
    }, 3000);
  };

  // Drag & drop file handler — text files only
  const TEXT_EXTENSIONS = ['.txt', '.md', '.py', '.json', '.csv', '.js', '.ts', '.xml', '.yaml', '.yml', '.log', '.html', '.css'];
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!TEXT_EXTENSIONS.includes(ext)) {
        showToast(`不支持 ${ext} 文件，请上传纯文本文件（.txt .md .py .json .csv 等）`);
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string || "";
        setUploadedFiles(prev => [...prev, { name: file.name, size: (file.size / 1024).toFixed(1) + " KB", content: text }]);
        setContextText(prev => prev + `\n\n[文献附加内容 - ${file.name}]:\n${text}`);
        showToast(`附加文件 ${file.name} 载入成功`);
      };
      reader.readAsText(file);
    }
  };

  const removeUploadedFile = (idx: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== idx));
  };

  // Per-tab file removal helpers
  const removeReportFile = (idx: number) => { setReportFiles(prev => prev.filter((_, i) => i !== idx)); };
  const removeOutlineFile = (idx: number) => { setOutlineFiles(prev => prev.filter((_, i) => i !== idx)); };
  const removeThesisFile = (idx: number) => { setThesisFiles(prev => prev.filter((_, i) => i !== idx)); };
  const removeReviewFile = (idx: number) => { setReviewFiles(prev => prev.filter((_, i) => i !== idx)); };
  const removeAgentFile = (idx: number) => { setAgentFiles(prev => prev.filter((_, i) => i !== idx)); };

  // Per-tab file drop handlers
  const handleFileDropTab = (e: React.DragEvent<HTMLDivElement>, setFiles: any, setContext: any) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      const TEXT_EXTENSIONS = ['.txt', '.md', '.py', '.json', '.csv', '.js', '.ts', '.xml', '.yaml', '.yml', '.log', '.html', '.css'];
      if (!TEXT_EXTENSIONS.includes(ext)) {
        showToast(`不支持 ${ext} 文件`);
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string || "";
        setFiles((prev: any) => [...prev, { name: file.name, size: (file.size / 1024).toFixed(1) + " KB", content: text }]);
        setContext((prev: string) => prev + `\n\n[文献附加内容 - ${file.name}]:\n${text}`);
        showToast(`附加文件 ${file.name} 载入成功`);
      };
      reader.readAsText(file);
    }
  };

  // Per-tab history load helpers
  const loadHistoryToContextTab = async (selectedId: string, setContext: any) => {
    if (!selectedId) { showToast("请选择一条历史记录"); return; }
    // Content is already preloaded in historyReports from GET /api/history
    const found = historyReports.find((h: any) => h.id === selectedId);
    const content = found?.content || "";
    if (content) {
      setContext((prev: string) => prev + `\n\n[历史记录引用 - ${selectedId}]:\n${content.slice(0, 3000)}`);
      showToast("历史记录已加载到上下文");
    } else {
      showToast("历史记录内容为空");
    }
  };

  // Provider selector change handler
  const handleProviderChange = (providerName: string) => {
    setSelectedProvider(providerName);
    const p = providersList.find((x: any) => x.name === providerName);
    if (p && p.default_model) {
      setSelectedModel(p.default_model);
    }
  };

  // Render provider/model selector (shared across tabs)
  const renderProviderSelector = () => (
    <div className="flex gap-2 items-center">
      <div className="flex-1">
        <select
          value={selectedProvider}
          onChange={e => handleProviderChange(e.target.value)}
          className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">-- 默认供应商 --</option>
          {providersList.map((p: any) => (
            <option key={p.name} value={p.name}>{p.display_name}</option>
          ))}
        </select>
      </div>
      {selectedProvider && (
        <div className="flex-1">
          <select
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
            className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {(() => {
              const p = providersList.find((x: any) => x.name === selectedProvider);
              const models = sniffedModels.length > 0 ? sniffedModels : (p ? [{ id: p.default_model || 'default' }] : []);
              return models.map((m: any) => (
                <option key={m.id} value={m.id}>{m.id}</option>
              ));
            })()}
          </select>
        </div>
      )}
    </div>
  );

  // Render context accordion (shared across tabs)
  const renderContextAccordion = (
    expanded: boolean, setExpanded: any,
    context: string, setContext: any,
    files: Array<{ name: string; size: string; content: string }>, setFiles: any,
    removeFile: any,
    historyId: string, setHistoryId: any,
  ) => (
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
            onDrop={(e) => handleFileDropTab(e, setFiles, setContext)}
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
                    <button onClick={() => removeFile(fIdx)} className="p-0.5 rounded hover:bg-gray-200 text-rose-500">
                      <X className="w-3 h-3" />
                    </button>
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
                <button onClick={() => loadHistoryToContextTab(historyId, setContext)} className="whitespace-nowrap shrink-0 text-[10px] font-semibold text-white bg-indigo-600 border border-indigo-500 px-4 py-2 rounded-lg hover:bg-indigo-700">加载</button>
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

  // Helper: Assemble request headers
  const getRequestHeaders = () => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }
    return headers;
  };

  // Helper: Compile base URL
  const getRequestUrl = (endpoint: string) => {
    // If customized API url exists, use that. Otherwise use local relative endpoint
    const base = apiUrl.trim().replace(/\/$/, "");
    return base ? `${base}/api${endpoint}` : `/api${endpoint}`;
  };

  // API Client triggers
  const handleStopExecution = () => {
    clearAllTimers();
    // Signal backend cancellation
    const rid = currentRequestIdRef.current;
    if (rid) {
      fetch(`/api/cancel/${rid}`, { method: "POST" }).catch(() => {});
    }
    setIsLoading(false);
    setProgressLogs(prev => [...prev, "⚠️ 已由用户手动中断执行。已截获阶段计算结果。"]);
    showToast("计算强行中断");
  };

  // General trigger execution handler for standard tabs
  const handleRunTask = async (taskType: Tab) => {
    if (isLoading) return;
    clearAllTimers();
    setIsLoading(true);
    setProgressLogs([]);
    setCurrentMarkdown("");
    setAgentExchanges([]);

    let requestBody = {};
    let endpoint = "";
    let activeTitle = "";

    // Assemble payload
    switch (taskType) {
      case "assistant":
        endpoint = "/assistant";
        activeTitle = `智能问答: ${assistantPrompt.slice(0, 15)}...`;
        requestBody = {
          prompt: assistantPrompt,
          context: contextText,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      case "report":
        endpoint = "/report";
        activeTitle = `报告生成: ${reportSubject}`;
        requestBody = {
          subject: reportSubject,
          field: reportField,
          depth: reportDepth,
          includeCharts: includeCharts,
          referenceCount: referenceCount,
          context: reportContext,
          skill_override: skillOverride,
          mcp_servers: selectedMcpServers,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      case "outline":
        endpoint = "/outline";
        activeTitle = `大纲设计: ${outlineSubject}`;
        requestBody = {
          subject: outlineSubject,
          field: outlineField,
          paper_type: outlinePaperType,
          context: outlineContext,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      case "thesis":
        endpoint = "/thesis";
        activeTitle = `段落撰写: ${thesisBlock}`;
        requestBody = {
          blockTitle: thesisBlock,
          prompt: thesisPrompt,
          style: thesisStyle,
          paper_type: thesisPaperType,
          length: thesisLength,
          context: thesisContext,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      case "review":
        endpoint = "/literature-review";
        activeTitle = `综述合成: ${reviewKeyword}`;
        requestBody = {
          keyword: reviewKeyword,
          sourceCount: reviewSourceCount,
          scope: reviewScope,
          taxonomy: reviewTaxonomy,
          comparisons: reviewComparisons,
          context: reviewContext,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      case "agents":
        endpoint = "/agents-collaborate";
        activeTitle = `多智能体协作: ${agentTopic}`;
        requestBody = {
          topic: agentTopic,
          doc_type: agentDocType,
          iterations: agentIterations,
          context: agentContext,
          provider: selectedProvider,
          model: selectedModel
        };
        break;
      default:
        setIsLoading(false);
        return;
    }

    setProgressLogs(["📡 正在连接 CS599 后端服务...", "📊 正在发送请求..."]);
    
    const addMessage = (msg: string) => {
      setProgressLogs(prev => [...prev, msg]);
    };

    // Generate request ID for cancellation support
    const requestId = "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    currentRequestIdRef.current = requestId;

    // ⏳ Heartbeat: show periodic "still waiting" message while fetch is pending
    let beatCount = 0;
    const heartbeatId = setInterval(() => {
      beatCount++;
      addMessage(`⏳ 模型正在处理中... (${beatCount * 15}s)`);
    }, 15000);
    timerRefs.current.push(heartbeatId as unknown as ReturnType<typeof setTimeout>);

    // Create AbortController for manual cancellation (no auto-timeout;
    // the backend has its own 240 s timeout.  The user stops via the
    // "停止" button, which calls clearAllTimers → controller.abort().)
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // Trigger real network call with request_id injected into body
      const res = await fetch(getRequestUrl(endpoint), {
        method: "POST",
        headers: getRequestHeaders(),
        body: JSON.stringify({ ...requestBody, request_id: requestId }),
        signal: controller.signal,
      });

      // ⚠️ 只能清除定时器，不能 abort controller！
      // controller.abort() 会取消正在传输的响应体流，
      // 导致下一行 res.json() 抛出 AbortError 进入 catch 块。
      timerRefs.current.forEach(clearTimeout);
      timerRefs.current = [];

      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          errMsg = errData.message || errData.detail || errMsg;
        } catch { /* ignore parse error */ }

        if (res.status === 401) {
          throw new AuthError(errMsg);
        }
        throw new HttpError(res.status, errMsg);
      }

      const data = await res.json();

      // Clear simulated logs and show real ones
      setProgressLogs([]);

      // Append server returned logs
      if (data.logs && Array.isArray(data.logs)) {
        data.logs.forEach((logItem: string, idx: number) => {
          setTimeout(() => {
            setProgressLogs(prev => [...prev, logItem]);
          }, (idx + 1) * 300);
        });
      }

      const delayMs = (data.logs ? data.logs.length * 300 : 300) + 200;
      setTimeout(() => {
        if (taskType === "agents" && data.exchange) {
          setAgentExchanges(data.exchange);
        }
        setCurrentMarkdown(data.markdown || "未能返回有效技术文献。");

        // Append new generated result to left histories list
        const newItem: HistoryItem = {
          id: "gen_" + Date.now(),
          timestamp: new Date().toISOString().replace("T", " ").substring(0, 16),
          type: taskType === "assistant" ? "智能助手" :
                taskType === "report" ? "研究报告" :
                taskType === "outline" ? "大纲生成" :
                taskType === "thesis" ? "学术论文" :
                taskType === "review" ? "综述写作" : "多智能体协作",
          title: activeTitle,
          content: data.markdown || ""
        };
        setHistory(prev => [newItem, ...prev]);

        // 刷新历史记录下拉框，新生成的报告立即可见
        fetchHistoryReports();

        setIsLoading(false);
        showToast("研讨内容生成成功，已记录至历史存档");
      }, delayMs);

    } catch (err: any) {
      clearAllTimers();

      console.error(err);

      // Determine error type and show appropriate message
      if (err?.name === "AbortError" || err?.name === "TimeoutError") {
        addMessage("⏱️ 请求超时: 后端处理时间超过 120 秒");
        addMessage("💡 解决方案: 可尝试简化问题描述，或检查后端模型服务状态");
        setCurrentMarkdown("### ⏱️ 请求超时\n\n后端处理时间超过 120 秒，请求已被中止。\n\n可尝试：\n1. 简化问题描述或减少生成内容篇幅\n2. 检查后端模型 API 服务是否正常\n3. 在「服务商管理」中更换响应更快的模型");
      } else if (err instanceof AuthError || err?.message?.includes("401")) {
        addMessage("🔑 认证失败: API Key 无效或未配置");
        addMessage("💡 解决方案: 请在「服务商管理」中检查并重新配置有效的 API Key");
        setCurrentMarkdown("### 🔑 API Key 认证失败\n\n请确认已在「服务商管理」中：\n1. 选择正确的供应商\n2. 输入有效的 API Key\n3. 点击「保存」并验证健康状态");
      } else if (err instanceof HttpError) {
        addMessage(`🔴 后端返回错误 [HTTP ${err.status}]: ${err.message}`);
        addMessage("💡 解决方案: 查看上方日志控制台获取详细错误信息");
        setCurrentMarkdown(`### ⚠️ 后端请求失败 [HTTP ${err.status}]\n\n**错误详情**: ${err.message}\n\n请查看日志控制台获取更多信息。`);
      } else if (err instanceof TypeError || err?.message?.includes("Failed to fetch") || err?.message?.includes("NetworkError")) {
        addMessage("🔴 无法连接后端: 请确认 FastAPI 后端正在运行（默认 :8000）");
        addMessage("💡 解决方案: 在终端中启动后端: `uvicorn src.api.server:app --reload --port 8000`");
        setCurrentMarkdown("### ⚠️ 后端未连接\n\n请确认 FastAPI 后端正在运行（默认 :8000），然后刷新页面重试。\n\n```bash\ncd cs599-project-v2\nuvicorn src.api.server:app --reload --port 8000\n```");
      } else {
        addMessage(`🔴 请求失败: ${err.message || "未知错误"}`);
        addMessage(`📍 请求地址: ${getRequestUrl(endpoint)}`);
        addMessage("💡 解决方案: 查看浏览器控制台 (F12) 获取更详细的错误信息");
        setCurrentMarkdown(`### ⚠️ 请求失败\n\n**错误**: ${err.message || "未知错误"}\n\n**请求地址**: ${getRequestUrl(endpoint)}\n\n请检查网络连接和后端状态。`);
      }

      setIsLoading(false);
    }
  };

  // Custom error classes for differentiated error handling
  class HttpError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = "HttpError";
      this.status = status;
    }
  }

  class AuthError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "AuthError";
    }
  }

  // Helper component to display beautifully parsed Chinese markdown styling inside a customized elegant card
  const MarkdownRenderer = ({ text }: { text: string }) => {
    if (!text) return null;

    // A fast, elegant line parser that formats Headings, list bullets, code blocks, tables and quotes inside beautiful UI containers
    const lines = text.split("\n");
    let insideCodeBlock = false;
    let codeBlockLines: string[] = [];
    let insideTable = false;
    let tableHeadings: string[] = [];
    let tableRows: string[][] = [];

    const elements: React.ReactNode[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code block start/end toggle
      if (line.trim().startsWith("```")) {
        if (insideCodeBlock) {
          insideCodeBlock = false;
          const codeText = codeBlockLines.join("\n");
          elements.push(
            <div key={`code-${i}`} className="my-3 font-mono text-xs overflow-x-auto bg-[#1E293B] text-slate-100 p-4 border-l-4 border-cyan-500 rounded-r-xl shadow-inner relative group">
              <div className="absolute top-2 right-2 text-[10px] uppercase bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-sans select-none opacity-0 group-hover:opacity-100 transition-opacity">
                代码片段
              </div>
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

      // Read markdown formatted table structures
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        const columns = line.split("|").slice(1, -1).map(col => col.trim());
        
        // Skip separator line (-|---|-)
        if (columns.every(col => col === "" || col.startsWith("---") || col.startsWith(":-") || col.startsWith("-:"))) {
          continue;
        }

        if (!insideTable) {
          insideTable = true;
          tableHeadings = columns;
          tableRows = [];
        } else {
          tableRows.push(columns);
        }
        continue;
      } else {
        if (insideTable) {
          insideTable = false;
          const currentTableIndex = i;
          elements.push(
            <div key={`table-${i}`} className="my-4 overflow-x-auto border border-gray-200 rounded-xl bg-white shadow-sm">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    {tableHeadings.map((head, hIdx) => (
                      <th key={`h-${hIdx}`} className="py-3 px-4 font-semibold text-gray-700">{head}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {tableRows.map((row, rIdx) => (
                    <tr key={`r-${rIdx}`} className="hover:bg-slate-50/55 transition-colors">
                      {row.map((val, cIdx) => (
                        <td key={`c-${cIdx}`} className="py-2.5 px-4 text-gray-600 font-sans leading-relaxed">{val}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
      }

      // Standard headings
      if (line.startsWith("### ")) {
        elements.push(
          <h3 key={i} className="text-sm font-semibold text-gray-800 mt-6 mb-3 flex items-center gap-2 border-b border-gray-100 pb-1.5 font-sans tracking-wide">
            <span className="w-1.5 h-4 bg-indigo-500 rounded-sm inline-block"></span>
            {line.replace("### ", "")}
          </h3>
        );
      } else if (line.startsWith("#### ")) {
        elements.push(
          <h4 key={i} className="text-xs font-semibold text-gray-700 mt-4 mb-2 font-sans tracking-wide">
            {line.replace("#### ", "")}
          </h4>
        );
      } else if (line.startsWith("## ")) {
        elements.push(
          <h2 key={i} className="text-base font-bold text-gray-900 mt-8 mb-4 border-b pb-2 font-sans tracking-wide">
            {line.replace("## ", "")}
          </h2>
        );
      } else if (line.startsWith("# ")) {
        elements.push(
          <h1 key={i} className="text-lg font-bold text-gray-950 mt-10 mb-6 font-sans tracking-tight">
            {line.replace("# ", "")}
          </h1>
        );
      }
      // Bullet lists
      else if (line.startsWith("- ") || line.startsWith("* ")) {
        elements.push(
          <li key={i} className="ml-5 list-disc text-xs text-gray-600 leading-relaxed my-1.5 font-sans">
            {line.substring(2)}
          </li>
        );
      }
      // Index lists
      else if (/^\d+\.\s/.test(line)) {
        const dotIdx = line.indexOf(". ");
        elements.push(
          <div key={i} className="ml-4 flex gap-2 items-start text-xs text-gray-600 leading-relaxed my-1.5 font-sans">
            <span className="font-semibold text-indigo-500 min-w-4 select-none">{line.substring(0, dotIdx + 1)}</span>
            <span>{line.substring(dotIdx + 2)}</span>
          </div>
        );
      }
      // Quotes
      else if (line.startsWith("> ")) {
        elements.push(
          <blockquote key={i} className="pl-4 border-l-4 border-indigo-400 bg-indigo-50/40 py-2 my-3 rounded-r-xl text-xs text-indigo-900 font-sans italic leading-relaxed">
            {line.replace("> ", "")}
          </blockquote>
        );
      }
      // Empty lines
      else if (line.trim() === "") {
        continue;
      }
      // Regular text paragraphs
      else {
        elements.push(
          <p key={i} className="text-xs text-gray-600 leading-relaxed font-sans my-2.5">
            {line}
          </p>
        );
      }
    }

    return <div className="space-y-1">{elements}</div>;
  };

  // Load history report from backend API into context
  const [selectedHistoryId, setSelectedHistoryId] = useState<string>("");
  const loadHistoryToContext = async () => {
    if (!selectedHistoryId) { showToast("请选择一条历史记录"); return; }
    try {
      const r = await fetch(`/api/history/${selectedHistoryId}`);
      if (r.ok) {
        const d = await r.json();
        const content = d.content || "";
        setContextText(prev => prev + `\n\n[历史记录引用 - ${d.id}]:\n${content.slice(0, 3000)}`);
        showToast("历史记录已加载到上下文");
      }
    } catch (_) { showToast("历史记录加载失败"); }
  };

  // Trash click deletes key from history
  const handleDeleteHistoryItem = (hId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setHistory(prev => prev.filter(item => item.id !== hId));
    // Also delete from server if it's a server-side ID (not gen_ prefix)
    if (!hId.startsWith("gen_")) {
      fetch(`/api/history/${hId}`, { method: "DELETE" }).catch(() => {});
    }
    showToast("已成功从本地视图删除该历史条目");
  };

  // Click pre-saved card in history, populates content instantly and shows it on Results screen!
  const handleLoadHistoryContent = async (item: HistoryItem) => {
    // Show loading feedback immediately
    setCurrentMarkdown("# 📂 正在加载历史记录...\n\n请稍候，正在从本地存储读取内容。");
    setProgressLogs(["📂 正在加载历史快照...", `📄 标题: ${item.title}`]);

    let content = item.content;
    if (!content) {
      try {
        const r = await fetch(`/api/history/${item.id}`);
        if (r.ok) {
          const d = await r.json();
          content = d.content || "";
        }
      } catch (_) {}
    }

    setCurrentMarkdown(content || "无法加载该历史记录的内容。");
    setProgressLogs(["📂 已成功加载历史快照！", `📥 ID: ${item.id}`, `📄 标题: ${item.title}`]);
    
    // Switch to respective UI tabs
    if (item.type === "智能助手") setActiveTab("assistant");
    else if (item.type === "研究报告") setActiveTab("report");
    else if (item.type === "大纲生成") setActiveTab("outline");
    else if (item.type === "学术论文") setActiveTab("thesis");
    else if (item.type === "综述写作") setActiveTab("review");
    else if (item.type === "多智能体协作") setActiveTab("agents");

    showToast(`载入快照: ${item.title}`);
  };

  return (
    <div id="cs599-outer-canvas" className="flex h-screen w-full items-center justify-center bg-gradient-to-tr from-[#E2E8F0] via-[#F1F5F9] to-[#F8FAFC] p-0 text-slate-800 font-sans overflow-hidden antialiased">
      
      {/* Toast Alert Badge */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 bg-indigo-600 text-white px-5 py-3 rounded-xl shadow-2xl border border-indigo-400 text-sm font-semibold animate-pulse">
          <Sparkles className="w-5 h-5 text-yellow-300" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* FLOATING WINDOW FRAME FOR EXTREME DESIGN PREMIUM FEEL */}
      <div id="cs599-app-frame" className="flex h-full w-full md:rounded-[32px] overflow-hidden bg-white/70 backdrop-blur-xl border border-white/60 shadow-[0_30px_70px_-15px_rgba(15,23,42,0.18)]">
        
        {/* LEFT SIDEBAR: CS599 v2.0 - PREMIUM FROSTED GLASS */}
        <aside className="w-80 flex flex-col bg-[#0B0F17]/90 backdrop-blur-3xl text-slate-300 border-r border-[#1F2937]/30 select-none shrink-0 relative overflow-hidden">
          
          {/* Ambient subtle light-source reflection behind the sidebar head */}
          <div className="absolute top-0 left-1/4 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full pointer-events-none"></div>

          {/* App Title Header */}
          <div className="p-6 border-b border-white/[0.04] flex items-center justify-between relative z-10">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-[#2563EB] to-cyan-500 rounded-2xl text-white shadow-lg shadow-indigo-500/20 border border-white/15">
                <Brain className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-lg font-bold text-white tracking-wide font-sans">CS599</span>
                  <span className="text-[9px] font-mono font-semibold text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded-full border border-cyan-800">v2.0</span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium tracking-wide">高级科研级学术引擎</p>
              </div>
            </div>
          </div>

          {/* Dynamic Sidebar Navigation Menu */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-7 relative z-10">
            
            {/* History Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-3 text-[10px] font-bold text-slate-500 tracking-wider uppercase">
                <span>历史记录</span>
                <span className="text-[9px] font-mono lowercase bg-white/5 text-slate-300 px-2 py-0.5 rounded-full border border-white/[0.02]">{history.length}</span>
              </div>
              
              {history.length === 0 ? (
                <div className="text-[11px] text-slate-500 px-3 py-3.5 bg-white/[0.02] rounded-2xl border border-dashed border-white/[0.06] text-center font-sans">
                  暂无学术生成归档记录
                </div>
              ) : (
                <div className="space-y-1.5">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleLoadHistoryContent(item)}
                      className="group flex items-center justify-between py-2 px-3.5 rounded-full bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.05] hover:border-white/[0.1] transition-all duration-200 cursor-pointer relative"
                    >
                      <div className="flex-1 min-w-0 pr-2">
                        <div className="text-[9px] font-mono text-slate-500 flex items-center gap-1.5 mb-0.5">
                          <span>{item.timestamp.split(" ")[1] || item.timestamp}</span>
                          <span className="text-[8px] text-cyan-400 bg-cyan-950/40 px-1.5 py-0.5 rounded-full font-sans border border-cyan-950/50">
                            {item.type}
                          </span>
                        </div>
                        <h4 className="text-xs font-medium text-slate-300 truncate font-sans group-hover:text-white transition-colors">
                          {item.title}
                        </h4>
                      </div>
                      
                      <button
                        onClick={(e) => handleDeleteHistoryItem(item.id, e)}
                        className="p-1 rounded-full text-slate-600 hover:text-rose-400 hover:bg-rose-950/20 transition-colors"
                        title="删除这则历史纪实"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Work Modes Nav Section */}
            <div className="space-y-1.5">
              <span className="block px-3 text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-3">
                工作模式
              </span>
              
              {/* 1. 智能助手 Tab */}
              <button
                onClick={() => setActiveTab("assistant")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "assistant"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>智能助手</span>
              </button>

              {/* 2. 研究报告 tab */}
              <button
                onClick={() => setActiveTab("report")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "report"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>研究报告</span>
              </button>

              {/* 3. 大纲生成 Tab */}
              <button
                onClick={() => setActiveTab("outline")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "outline"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>大纲生成</span>
              </button>

              {/* 4. 学术论文 Tab */}
              <button
                onClick={() => setActiveTab("thesis")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "thesis"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>学术论文</span>
              </button>

              {/* 5. 综述写作 Tab */}
              <button
                onClick={() => setActiveTab("review")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "review"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>综述写作</span>
              </button>

              {/* 6. 多智能体协作 Tab */}
              <button
                onClick={() => setActiveTab("agents")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "agents"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>多智能体协作</span>
              </button>

              {/* 7. 技能管理 Tab */}
              <button
                onClick={() => setActiveTab("skills")}
                className={`w-full py-2.5 text-xs font-semibold font-sans tracking-wide transition-all duration-200 text-center ${
                  activeTab === "skills"
                    ? "bg-gradient-to-r from-blue-600 to-[#1D4ED8] text-white shadow-lg shadow-blue-500/25 rounded-full border border-blue-500/10 scale-[1.01]"
                    : "hover:bg-white/[0.05] text-slate-400 hover:text-slate-100 rounded-full"
                }`}
              >
                <span>技能管理</span>
              </button>
            </div>
          </div>

          {/* Footer controls: Provider Admin / Settings */}
          <div className="p-4 bg-black/20 border-t border-white/[0.04] space-y-2 relative z-10">
            <button
              onClick={() => setActiveTab("providers")}
              className={`w-full flex items-center justify-center gap-2 py-2 rounded-full text-xs font-medium font-sans transition-all duration-200 ${
                activeTab === "providers"
                  ? "bg-white/10 text-white border border-white/10"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]"
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              <span>服务商管理</span>
            </button>
            
            <button
              onClick={() => setActiveTab("settings")}
              className={`w-full flex items-center justify-center gap-2 py-2 rounded-full text-xs font-medium font-sans transition-all duration-200 ${
                activeTab === "settings"
                  ? "bg-white/10 text-white border border-white/10"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]"
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              <span>设置</span>
            </button>
          </div>
        </aside>

        {/* RIGHT WORKSPACE INTERACTIVE PANELS */}
        <main className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50">
          
          {/* TOP STATUS NAVIGATION BAR */}
          <header className="h-16 px-8 bg-white/80 backdrop-blur-md border-b border-gray-100 flex items-center justify-between select-none shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 font-medium">CS599 工作站</span>
              <span className="text-xs text-gray-300">/</span>
            <span className="text-xs text-indigo-500 font-semibold uppercase">{activeTab === "review" ? "综述" : activeTab === "agents" ? "协同" : activeTab === "providers" ? "服务" : activeTab}</span>
          </div>

          <div className="flex items-center gap-4">
            {/* Quick status dots */}
            <div className="flex items-center gap-2 text-xs bg-indigo-50 text-indigo-700 border border-indigo-100/50 py-1.5 px-3 rounded-full font-medium">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
              <span>
                后端就绪
              </span>
            </div>
          </div>
        </header>

        {/* WORKSPACE CENTRAL SPLIDER */}
        {!backendOnline && (
              <div className="mx-4 mt-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-800 font-sans flex items-center gap-2 shrink-0">
                <span>⚠️</span>
                <span>FastAPI 后端未连接（默认 :8000），部分功能不可用。请启动后端后刷新页面</span>
              </div>
            )}

        <section className="flex-1 flex overflow-hidden p-4 gap-4">
          
          {/* CONTROL SECTION (LEFT PANE) */}
          <div className="w-[380px] xl:w-[430px] flex flex-col gap-6 overflow-y-auto pr-2">
            
            {/* 1. TAB: 智能助手 */}
            {activeTab === "assistant" && (
              <div className="space-y-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight">智能助手</h2>
                    <div className="flex items-end gap-0.5 h-4 w-6 select-none bg-indigo-50 border border-indigo-100 p-1 rounded">
                      <div className="w-1 bg-[#2563EB] pulse-bar-1 rounded-sm h-full origin-bottom"></div>
                      <div className="w-1 bg-[#2563EB] pulse-bar-2 rounded-sm h-full origin-bottom"></div>
                      <div className="w-1 bg-[#2563EB] pulse-bar-3 rounded-sm h-full origin-bottom"></div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    输入您的科研设想或主题，助手将联动文献库开展深度大模型知识演练、计算归一化与技术报告编译。
                  </p>
                </div>

                {renderContextAccordion(isContextExpanded, setIsContextExpanded, contextText, setContextText, uploadedFiles, setUploadedFiles, removeUploadedFile, selectedHistoryId, setSelectedHistoryId)}

                {renderProviderSelector()}

                {/* Main Action Input Panel */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-2">研讨技术大题：</label>
                    <textarea
                      value={assistantPrompt}
                      onChange={(e) => setAssistantPrompt(e.target.value)}
                      placeholder="e.g., 帮助我研究多智能体协作的最新进展并写一份全面的总结。"
                      className="w-full h-32 p-4 text-xs font-sans border rounded-xl bg-white shadow-inner focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 leading-relaxed"
                    />
                  </div>

                  {/* Trigger buttons */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleRunTask("assistant")}
                      disabled={isLoading}
                      className={`flex-1 flex items-center justify-center gap-2 text-xs font-semibold py-3 px-6 rounded-full border transition-all text-white shadow-md ${
                        isLoading
                          ? "bg-indigo-400/80 cursor-not-allowed border-indigo-300"
                          : "bg-[#2563EB] hover:bg-blue-700 hover:scale-[1.01] border-blue-600 hover:shadow-indigo-500/20"
                      }`}
                    >
                      {isLoading ? (
                        <>
                          <span className="w-2 h-2 bg-white rounded-full animate-ping"></span>
                          <span>核心计算运行中 ...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 fill-white text-white" />
                          <span>执行助手计算流</span>
                        </>
                      )}
                    </button>

                    {isLoading && (
                      <button
                        onClick={handleStopExecution}
                        className="flex items-center justify-center gap-1.5 bg-rose-50 hover:bg-rose-100 hover:scale-[1.01] border border-rose-200 text-rose-600 text-xs font-semibold py-3 px-5 rounded-full transition-all"
                      >
                        <Square className="w-3.5 h-3.5 fill-rose-600 text-rose-600" />
                        <span>停止</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 2. TAB: 研究报告生成 */}
            {activeTab === "report" && (
              <div className="space-y-6 animate-fadeIn">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">研究报告生成 📄</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    配置完备的学术大纲参数，由 CS599 语义引擎检索并定制化产出完整的纵深研究报告文献。
                  </p>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">报告主题</label>
                    <input
                      value={reportSubject}
                      onChange={(e) => setReportSubject(e.target.value)}
                      type="text"
                      placeholder="例: 基于联邦状态控制的异步大模型对齐机制"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">研究领域</label>
                    <input
                      value={reportField}
                      onChange={(e) => setReportField(e.target.value)}
                      type="text"
                      placeholder="例: 计算神经科学 / 分布式博弈控制"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>

                  {/* Depth Selection Input Box */}
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-2">深度选择</label>
                    <div className="grid grid-cols-3 gap-3">
                      {(["基础", "详细", "专家"] as const).map((lvl) => (
                        <button
                          key={lvl}
                          onClick={() => setReportDepth(lvl)}
                          className={`py-2 px-3 text-xs font-semibold rounded-full border transition-all ${
                            reportDepth === lvl
                              ? "bg-indigo-50 border-indigo-400 text-indigo-700 shadow-sm"
                              : "bg-white border-gray-200 hover:border-gray-300 text-gray-600"
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Advanced settings cards block */}
                  <div className="pt-2 border-t border-gray-100 space-y-4">
                    <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-1 select-none">
                      高级选项
                    </span>

                    <div className="flex items-center justify-between bg-slate-50 border p-3.5 rounded-xl">
                      <div className="flex flex-col">
                        <span className="text-xs font-semibold text-gray-700">包含拟合图表</span>
                        <span className="text-[10px] text-gray-400">在Markdown内置模拟量化比对数据表</span>
                      </div>
                      
                      {/* Custom toggle slider */}
                      <button
                        onClick={() => setIncludeCharts(!includeCharts)}
                        className={`w-11 h-6 py-1 px-1 rounded-full border transition-colors flex ${
                          includeCharts ? "bg-[#2563EB] border-[#3B82F6] justify-end" : "bg-gray-200 border-gray-300 justify-start"
                        }`}
                      >
                        <span className="w-3.5 h-3.5 bg-white rounded-full shadow-md transition-transform" />
                      </button>
                    </div>

                    <div>
                      <div className="flex justify-between items-baseline mb-2 select-none">
                        <span className="text-xs font-semibold text-gray-700">参考来源数量</span>
                        <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                          {referenceCount}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] text-gray-400 select-none">1</span>
                        <input
                          type="range"
                          min="1"
                          max="20"
                          value={referenceCount}
                          onChange={(e) => setReferenceCount(Number(e.target.value))}
                          className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                        />
                        <span className="text-[10px] text-gray-400 select-none">20</span>
                      </div>
                    </div>
                  </div>
                </div>

                {renderProviderSelector()}

                {renderContextAccordion(reportContextExpanded, setReportContextExpanded, reportContext, setReportContext, reportFiles, setReportFiles, removeReportFile, reportHistoryId, setReportHistoryId)}

                <button
                  onClick={() => handleRunTask("report")}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-2 text-xs font-bold py-3.5 px-6 rounded-full text-white tracking-wide shadow-md bg-gradient-to-r from-indigo-600 to-cyan-500 hover:scale-[1.01] hover:from-indigo-700 hover:to-cyan-600 border-t border-white/20 select-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Sparkles className="w-4 h-4 fill-white text-cyan-300 animate-spin" />
                  <span>开始融合报告</span>
                </button>
              </div>
            )}

            {/* 3. TAB: 大纲生成 */}
            {activeTab === "outline" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">大纲生成 📄</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    快速建立完整的论文写作框架与重点章节控制，自动设计好合理的逻辑推导先后路线图。
                  </p>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">研究总议题</label>
                    <input
                      value={outlineSubject}
                      onChange={(e) => setOutlineSubject(e.target.value)}
                      type="text"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">大类领域</label>
                    <input
                      value={outlineField}
                      onChange={(e) => setOutlineField(e.target.value)}
                      type="text"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">论文类型</label>
                  <select value={outlinePaperType} onChange={e => setOutlinePaperType(e.target.value)} className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                    <option value="研究论文">研究论文</option>
                    <option value="综述论文">综述论文</option>
                    <option value="短论文">短论文</option>
                  </select>
                </div>

                {renderProviderSelector()}

                {renderContextAccordion(outlineContextExpanded, setOutlineContextExpanded, outlineContext, setOutlineContext, outlineFiles, setOutlineFiles, removeOutlineFile, outlineHistoryId, setOutlineHistoryId)}

                <button
                  onClick={() => handleRunTask("outline")}
                  disabled={isLoading}
                  className="w-full py-3 px-6 text-xs font-bold rounded-full text-white text-center tracking-wide bg-[#2563EB] hover:bg-blue-700 border border-blue-600 hover:scale-[1.01] shadow-md transition-all disabled:opacity-50"
                >
                  开始设计学术大纲
                </button>
              </div>
            )}

            {/* 4. TAB: 学术论文 */}
            {activeTab === "thesis" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">学术论文段落生成</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    输入您拟写章节的小标题与核心公式思路，高浓度的中英文混合式Nature/IEEE严谨论文段落将自动诞生。
                  </p>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">拟书写段落 / 章节标题</label>
                    <input
                      value={thesisBlock}
                      onChange={(e) => setThesisBlock(e.target.value)}
                      type="text"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">核心论点细节</label>
                    <textarea
                      value={thesisPrompt}
                      onChange={(e) => setThesisPrompt(e.target.value)}
                      className="w-full h-24 p-3 text-xs border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans leading-relaxed"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-2">学术叙事文风风格</label>
                    <div className="grid grid-cols-1 gap-2.5">
                      {["Nature标准格式", "ACM/IEEE 双栏通排范式", "深度研究专著体叙述"].map((st) => (
                        <button
                          key={st}
                          onClick={() => setThesisStyle(st)}
                          className={`w-full text-left px-4 py-3 text-xs font-semibold rounded-full border transition-all flex items-center justify-between ${
                            thesisStyle === st
                              ? "bg-indigo-50 border-indigo-400 text-indigo-700"
                              : "bg-white border-gray-200 hover:bg-slate-50/50 text-gray-600"
                          }`}
                        >
                          <span>{st}</span>
                          {thesisStyle === st && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">论文类型</label>
                      <select value={thesisPaperType} onChange={e => setThesisPaperType(e.target.value)} className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="research">研究论文</option>
                        <option value="survey">综述论文</option>
                        <option value="short">短论文</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">篇幅</label>
                      <select value={thesisLength} onChange={e => setThesisLength(e.target.value)} className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="short">短</option>
                        <option value="medium">中</option>
                        <option value="long">长</option>
                      </select>
                    </div>
                  </div>
                </div>

                {renderProviderSelector()}

                {renderContextAccordion(thesisContextExpanded, setThesisContextExpanded, thesisContext, setThesisContext, thesisFiles, setThesisFiles, removeThesisFile, thesisHistoryId, setThesisHistoryId)}

                <button
                  onClick={() => handleRunTask("thesis")}
                  disabled={isLoading}
                  className="w-full py-3.5 px-6 text-xs font-bold rounded-full text-white text-center tracking-wide bg-[#2563EB] hover:bg-blue-700 border border-blue-600 hover:scale-[1.01] shadow-md transition-all disabled:opacity-50"
                >
                  撰写论文段落
                </button>
              </div>
            )}

            {/* 5. TAB: 综述写作 */}
            {activeTab === "review" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">文献综述深度检索撰写 📚</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    给出核心研究关键字，自主抓取分析学术刊物时间线，构建带有对比表格的高级文献综述篇章。
                  </p>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">文献研搜关键词</label>
                    <input
                      value={reviewKeyword}
                      onChange={(e) => setReviewKeyword(e.target.value)}
                      type="text"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">对比分析文献数量</label>
                    <input
                      value={reviewSourceCount}
                      onChange={(e) => setReviewSourceCount(Number(e.target.value))}
                      type="number"
                      className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
                    />
                  </div>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">综述范围</label>
                    <select value={reviewScope} onChange={e => setReviewScope(e.target.value)} className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                      <option value="focused">聚焦 (Focused)</option>
                      <option value="broad">广泛 (Broad)</option>
                      <option value="comparative">对比 (Comparative)</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                      <input type="checkbox" checked={reviewTaxonomy} onChange={e => setReviewTaxonomy(e.target.checked)} className="rounded" />
                      包含分类法
                    </label>
                    <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                      <input type="checkbox" checked={reviewComparisons} onChange={e => setReviewComparisons(e.target.checked)} className="rounded" />
                      包含对比表
                    </label>
                  </div>
                </div>

                {renderProviderSelector()}

                {renderContextAccordion(reviewContextExpanded, setReviewContextExpanded, reviewContext, setReviewContext, reviewFiles, setReviewFiles, removeReviewFile, reviewHistoryId, setReviewHistoryId)}

                <button
                  onClick={() => handleRunTask("review")}
                  disabled={isLoading}
                  className="w-full py-3 px-6 text-xs font-bold rounded-full text-white text-center tracking-wide bg-[#2563EB] hover:bg-blue-700 border border-blue-600 hover:scale-[1.01] shadow-md transition-all disabled:opacity-50"
                >
                  开始检索并合成综述
                </button>
              </div>
            )}

            {/* 6. TAB: 多智能体协作 */}
            {activeTab === "agents" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">多智能体协同研讨论坛</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    呼唤科研助理集群：【搜索专家】负责扫清文献，【分析助手】进行量化评估，【写作专家】归拢观点。
                  </p>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">研讨核心问题 / 选题</label>
                    <textarea
                      value={agentTopic}
                      onChange={(e) => setAgentTopic(e.target.value)}
                      className="w-full h-24 p-3 text-xs border rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans leading-relaxed"
                    />
                  </div>
                </div>

                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">文档类型</label>
                    <select value={agentDocType} onChange={e => setAgentDocType(e.target.value)} className="w-full text-xs p-3 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                      <option value="report">研究报告</option>
                      <option value="paper">学术论文</option>
                      <option value="summary">摘要总结</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">审查轮数: {agentIterations}</label>
                    <input type="range" min="1" max="3" value={agentIterations} onChange={e => setAgentIterations(parseInt(e.target.value))} className="w-full accent-indigo-600" />
                    <div className="flex justify-between text-[10px] text-gray-400"><span>1</span><span>2</span><span>3</span></div>
                  </div>
                </div>

                {renderProviderSelector()}

                {renderContextAccordion(agentContextExpanded, setAgentContextExpanded, agentContext, setAgentContext, agentFiles, setAgentFiles, removeAgentFile, agentHistoryId, setAgentHistoryId)}

                <button
                  onClick={() => handleRunTask("agents")}
                  disabled={isLoading}
                  className="w-full py-3.5 px-6 rounded-full text-xs font-bold text-center tracking-wide text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-[1.01] shadow-md transition-all disabled:opacity-50"
                >
                  激活集群协作流程
                </button>
              </div>
            )}

            {/* 7. TAB: 技能管理 */}
            {activeTab === "skills" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">技能管理 🔬</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    启用的模块将在每次生成时自动注入编译流水线中。支持安装自定义技能。
                  </p>
                </div>

                {/* Install skill */}
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
                        <input
                          type="file"
                          accept=".py,.zip"
                          onChange={async (e) => {
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
                          }}
                          className="w-full text-xs p-2 border rounded-xl bg-slate-50/50 file:mr-3 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Skill list */}
                <div className="space-y-3">
                  {rawSkills.length > 0 && (
                    <div className="text-[10px] text-gray-400 font-medium">共 {rawSkills.length} 个技能</div>
                  )}
                  {skills.map((sk, idx) => {
                    const raw = rawSkills[idx] || {};
                    const isUser = raw.is_user_skill;
                    const tag = raw.tags?.[0] || sk.category;
                    return (
                      <div
                        key={sk.id}
                        className={`p-4 border rounded-2xl transition-all bg-white ${sk.isActive ? 'border-indigo-200 shadow-sm shadow-indigo-100/30' : 'border-gray-200'}`}
                      >
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
                            <div onClick={() => setSkills(prev => prev.map(item => item.id === sk.id ? { ...item, isActive: !item.isActive } : item))} className={`w-5 h-5 rounded-md border flex items-center justify-center cursor-pointer select-none transition-all ${sk.isActive ? 'bg-indigo-600 border-indigo-500 text-white' : 'border-gray-300 bg-white'}`}>
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
            )}

            {/* 8. TAB: 服务商管理 */}
            {activeTab === "providers" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-1">服务商管理 ⚙️</h2>
                    <p className="text-xs text-gray-500 leading-relaxed font-sans">
                      管理 LLM 服务商、MCP 服务器和搜索工具
                    </p>
                  </div>
                  <button onClick={refreshAll} className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold bg-indigo-50 px-3 py-1.5 rounded-full border border-indigo-100">⟳ 刷新</button>
                </div>

                {!backendOnline && providersList.length === 0 && (
                  <div className="p-6 bg-amber-50 border border-amber-200 rounded-2xl text-center">
                    <p className="text-xs text-amber-700 font-sans mb-2">⚠️ 无法连接后端服务，服务商列表不可用</p>
                    <p className="text-[11px] text-amber-600 font-sans">请确认 FastAPI 后端正在运行（默认 :8000），然后点击刷新</p>
                  </div>
                )}

                {/* --- LLM Providers --- */}
                <div>
                  <h3 className="text-sm font-bold text-gray-800 font-sans mb-3">🤖 LLM 服务商</h3>
                  <div className="space-y-3">
                    {providersList.map((p) => (
                      <div key={p.name} className="border border-gray-200 rounded-2xl bg-white p-4 shadow-sm">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className={`w-2 h-2 rounded-full ${providersHealth[p.name]?.healthy ? 'bg-emerald-500' : 'bg-gray-300'}`}></span>
                              <span className="text-sm font-semibold text-gray-800">{p.display_name}</span>
                              <code className="text-[9px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{p.name}</code>
                              <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${p.has_key ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-amber-50 text-amber-600 border border-amber-100'}`}>
                                {p.has_key ? '已配置' : '未配置'}
                              </span>
                            </div>
                            <p className="text-[10px] text-gray-400 font-mono truncate">Base URL: {p.base_url || '未配置'} | 模型: {p.default_model || '-'}</p>
                          </div>
                          <div className="flex items-center gap-1 shrink-0 ml-2">
                            <button onClick={() => startEdit(p)} className="text-[10px] text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded-lg border border-indigo-100">✏️</button>
                            {!['deepseek','openai','anthropic','siliconflow','openrouter','dashscope','kimi','zhipu','baidu','ollama'].includes(p.name) && (
                              <button onClick={() => deleteProvider(p.name)} className="text-[10px] text-rose-500 hover:bg-rose-50 px-2 py-1 rounded-lg border border-rose-100">🗑️</button>
                            )}
                          </div>
                        </div>

                        {/* Inline edit form */}
                        {editingProvider === p.name && (
                          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">Base URL</label>
                                <input value={editBaseUrl} onChange={e => setEditBaseUrl(e.target.value)} className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                              </div>
                              <div>
                                <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">默认模型</label>
                                <input value={editModel} onChange={e => setEditModel(e.target.value)} className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                              </div>
                            </div>
                            <div>
                              <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">API Key</label>
                              <input value={editApiKey} onChange={e => setEditApiKey(e.target.value)} type="password" placeholder="留空则不修改" className="w-full text-[11px] p-2 border rounded-lg bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                            </div>
                            <div className="flex gap-2">
                              <button onClick={() => sniffModels(p.name)} className="text-[10px] font-semibold text-cyan-700 bg-cyan-50 border border-cyan-100 px-3 py-1.5 rounded-full hover:bg-cyan-100">🔍 嗅探模型</button>
                              <button onClick={() => saveEdit(p.name)} className="text-[10px] font-bold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-1.5 rounded-full">保存</button>
                              <button onClick={() => setEditingProvider(null)} className="text-[10px] font-semibold text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-full border border-gray-200">取消</button>
                            </div>
                            {sniffedModels.length > 0 && editingProvider === p.name && (
                              <div className="mt-2 p-2 bg-cyan-50 border border-cyan-100 rounded-lg">
                                <span className="text-[9px] font-bold text-cyan-700 uppercase tracking-wider">已发现模型</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {sniffedModels.map((m: any) => (
                                    <button key={m.id} onClick={() => { setEditModel(m.id); setSelectedModel(m.id); }} className={`text-[9px] px-2 py-0.5 rounded-full border ${editModel === m.id ? 'bg-cyan-600 text-white border-cyan-600' : 'bg-white text-cyan-700 border-cyan-200 hover:bg-cyan-50'}`}>
                                      {m.id}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* --- Add Provider --- */}
                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm">
                  <h3 className="text-xs font-bold text-gray-800 font-sans mb-3">➕ 添加服务商</h3>
                  <div className="space-y-3">
                    <div>
                      <select value={addPresetName} onChange={e => { setAddPresetName(e.target.value); if (e.target.value !== "custom") setShowCustomProvider(false); }} className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="">-- 选择预设 --</option>
                        {presetsList.map((pr: any) => (
                          <option key={pr.name} value={pr.name}>{pr.display_name} ({pr.name})</option>
                        ))}
                        <option value="custom">🛠️ 自定义服务商</option>
                      </select>
                    </div>
                    {addPresetName === "custom" && (
                      <>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">名称</label>
                          <input value={customProviderName} onChange={e => setCustomProviderName(e.target.value)} placeholder="my-provider" className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">Base URL</label>
                          <input value={customProviderUrl} onChange={e => setCustomProviderUrl(e.target.value)} placeholder="https://api.example.com/v1" className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">API Key</label>
                          <input value={customProviderKey} onChange={e => setCustomProviderKey(e.target.value)} type="password" className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">默认模型</label>
                          <input value={customProviderModel} onChange={e => setCustomProviderModel(e.target.value)} placeholder="gpt-4" className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <button onClick={addCustomProviderFn} className="w-full py-2.5 px-4 rounded-full text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition-all shadow-sm">添加自定义服务商</button>
                      </>
                    )}
                    {addPresetName && addPresetName !== "custom" && (
                      <>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">自定义 Base URL (可选)</label>
                          <input value={addCustomUrl} onChange={e => setAddCustomUrl(e.target.value)} placeholder={presetsList.find((p: any) => p.name === addPresetName)?.base_url || ''} className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <div>
                          <label className="block text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">API Key</label>
                          <input value={addApiKey} onChange={e => setAddApiKey(e.target.value)} type="password" className="w-full text-xs p-2.5 border rounded-xl bg-slate-50/50 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono" />
                        </div>
                        <button onClick={addProvider} className="w-full py-2.5 px-4 rounded-full text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition-all shadow-sm">添加</button>
                      </>
                    )}
                  </div>
                </div>

                {/* --- MCP Management --- */}
                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm">
                  <h3 className="text-xs font-bold text-gray-800 font-sans mb-3">🔌 MCP 管理</h3>
                  <div className="space-y-4">
                    {/* Tavily */}
                    <div className="bg-slate-50/50 border border-gray-100 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-700">🚀 Tavily MCP 本地服务器</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${tavilyRunning ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
                          {tavilyRunning ? '运行中' : '未运行'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        <input value={tavilyProxy} onChange={e => setTavilyProxy(e.target.value)} placeholder="代理地址" className="text-[11px] p-2 border rounded-lg bg-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                        <input value={tavilyKey} onChange={e => setTavilyKey(e.target.value)} type="password" placeholder="Tavily Key" className="text-[11px] p-2 border rounded-lg bg-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                      </div>
                      {tavilyRunning ? (
                        <button onClick={stopTavily} className="text-[10px] font-semibold text-rose-600 bg-rose-50 border border-rose-100 px-3 py-1.5 rounded-full hover:bg-rose-100">⏹️ 停止</button>
                      ) : (
                        <button onClick={startTavily} className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-100 px-3 py-1.5 rounded-full hover:bg-emerald-100">▶️ 启动</button>
                      )}
                    </div>

                    {/* Remote MCP */}
                    <div className="bg-slate-50/50 border border-gray-100 rounded-xl p-4">
                      <span className="text-xs font-semibold text-gray-700 block mb-2">🌐 远程 MCP</span>
                      <div className="space-y-2">
                        <input value={remoteMcpUrl} onChange={e => setRemoteMcpUrl(e.target.value)} placeholder="MCP URL (SSE)" className="w-full text-[11px] p-2 border rounded-lg bg-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                        <input value={remoteMcpKey} onChange={e => setRemoteMcpKey(e.target.value)} type="password" placeholder="API Key (可选)" className="w-full text-[11px] p-2 border rounded-lg bg-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                        <button onClick={addRemoteMcp} className="text-[10px] font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 px-3 py-1.5 rounded-full hover:bg-indigo-100">添加远程 MCP</button>
                      </div>
                    </div>

                    {/* MCP Server List */}
                    {mcpServers.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">已注册 MCP</span>
                        {mcpServers.map((s: any) => (
                          <div key={s.name} className="flex items-center justify-between bg-white border border-gray-100 rounded-xl p-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`w-1.5 h-1.5 rounded-full ${s.is_active ? 'bg-emerald-500' : 'bg-gray-300'}`}></span>
                                <span className="text-xs font-semibold text-gray-700">{s.display_name}</span>
                                <code className="text-[9px] bg-slate-100 text-slate-500 px-1 py-0.5 rounded">{s.name}</code>
                                {s.is_active && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600">活跃</span>}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 shrink-0 ml-2">
                              <button onClick={() => toggleMcp(s.name)} className="text-[9px] text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded border border-indigo-100">{s.is_active ? '禁用' : '启用'}</button>
                              <button onClick={() => deleteMcp(s.name)} className="text-[9px] text-rose-500 hover:bg-rose-50 px-2 py-1 rounded border border-rose-100">🗑️</button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* --- Search API Keys --- */}
                <div className="border border-gray-200 rounded-2xl bg-white p-5 shadow-sm">
                  <h3 className="text-xs font-bold text-gray-800 font-sans mb-3">🔍 搜索工具 API Key</h3>
                  <div className="space-y-3">
                    {searchBackends.length === 0 ? (
                      <div className="flex items-center justify-between bg-slate-50/50 border border-gray-100 rounded-xl p-3">
                        <div>
                          <span className="text-xs font-semibold text-gray-700">DuckDuckGo</span>
                          <p className="text-[10px] text-gray-400">免费，无需 API Key</p>
                        </div>
                        <span className="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">可用</span>
                      </div>
                    ) : (
                      searchBackends.map((b: any) => (
                        <div key={b.name} className="bg-slate-50/50 border border-gray-100 rounded-xl p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <span className="text-xs font-semibold text-gray-700">{b.display_name}</span>
                              <p className="text-[10px] text-gray-400">{b.description}</p>
                            </div>
                          </div>
                          {b.requires_key && (
                            <div className="flex gap-2">
                              <input
                                value={b.name === 'brave' ? braveSearchKey : b.name === 'semantic_scholar' ? semanticScholarKey : bochaSearchKey}
                                onChange={e => { if (b.name === 'brave') setBraveSearchKey(e.target.value); else if (b.name === 'semantic_scholar') setSemanticScholarKey(e.target.value); else setBochaSearchKey(e.target.value); }}
                                type="password" placeholder="输入 API Key（可选）"
                                className="flex-1 text-[11px] p-2 border rounded-lg bg-white font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                              <button onClick={() => saveSearchKey(b.name, b.name === 'brave' ? braveSearchKey : b.name === 'semantic_scholar' ? semanticScholarKey : bochaSearchKey)} className="text-[10px] font-semibold text-white bg-slate-900 hover:bg-slate-800 px-3 py-1.5 rounded-full">保存</button>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 9. TAB: 设置 */}
            {activeTab === "settings" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-950 font-sans tracking-tight mb-2">系统偏好设置 🛠️</h2>
                  <p className="text-xs text-gray-500 leading-relaxed font-sans">
                    调节学术格式化模版与全局提示语约束，自定义您的研写系统习惯。
                  </p>
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
            )}

          </div>

          {/* RESULTS DISPLAY PANE (RIGHT MAIN WORKSPACE BOX) */}
          <div className="flex-1 flex flex-col h-full bg-white border border-gray-100 rounded-3xl overflow-hidden shadow-sm relative">
            
            {/* AGENT GRAPH OR FLOATING TERMINAL OVERLAY (ONLY SHOWN FOR AGENT WORK Tab) */}
            {activeTab === "agents" && (
              <div className="p-6 bg-slate-50/55 border-b border-gray-100 select-none shrink-0">
                <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-4">
                  智能体网络拓扑
                </span>
                
                {/* 3 Nodes visual diagram */}
                <div className="flex items-center justify-center p-4 relative h-48 bg-white border rounded-2xl shadow-inner overflow-hidden">
                  
                  {/* CSS SVG custom lines flow */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none select-none">
                    <path
                      id="search-to-analysis"
                      d="M 120,96 C 180,96 180,96 230,96"
                      fill="none"
                      stroke="#E2E8F0"
                      strokeWidth="2.5"
                    />
                    <path
                      id="analysis-to-writer"
                      d="M 330,96 C 390,96 390,96 440,96"
                      fill="none"
                      stroke="#E2E8F0"
                      strokeWidth="2.5"
                    />
                    
                    {/* Glowing flow dots traveling during generation load */}
                    {isLoading && (
                      <>
                        <circle r="4" fill="#3B82F6" className="animate-flow-dot">
                          <animateMotion dur="2.5s" repeatCount="indefinite" path="M 120,96 C 180,96 180,96 230,96" />
                        </circle>
                        <circle r="4" fill="#10B981" className="animate-flow-dot">
                          <animateMotion dur="2.2s" repeatCount="indefinite" path="M 330,96 C 390,96 390,96 440,96" />
                        </circle>
                      </>
                    )}
                  </svg>

                  {/* 1. Node Search */}
                  <div className="absolute left-6 z-10 text-center flex flex-col items-center gap-1.5">
                    <div className={`p-4 bg-white border-2 rounded-2xl shadow-md transition-all ${
                      isLoading ? "border-blue-500 scale-105 animate-pulse" : "border-gray-200"
                    }`}>
                      <Search className={`w-5 h-5 ${isLoading ? "text-blue-500" : "text-gray-500"}`} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-700">搜索专家</span>
                    <span className="text-[8px] text-gray-400 max-w-[85px] truncate">负责检索筛选文献</span>
                  </div>

                  {/* 2. Node Analysis */}
                  <div className="absolute z-10 text-center flex flex-col items-center gap-1.5">
                    <div className={`p-4 bg-white border-2 rounded-2xl shadow-md transition-all ${
                      isLoading ? "border-amber-500 scale-105 animate-pulse" : "border-gray-200"
                    }`}>
                      <Activity className={`w-5 h-5 ${isLoading ? "text-amber-500" : "text-gray-500"}`} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-700">分析助手</span>
                    <span className="text-[8px] text-gray-400 max-w-[85px] truncate">进行模型复杂度评估</span>
                  </div>

                  {/* 3. Node Writer */}
                  <div className="absolute right-6 z-10 text-center flex flex-col items-center gap-1.5">
                    <div className={`p-4 bg-white border-2 rounded-2xl shadow-md transition-all ${
                      isLoading ? "border-emerald-500 scale-105 animate-pulse" : "border-gray-200"
                    }`}>
                      <FileCode className={`w-5 h-5 ${isLoading ? "text-emerald-500" : "text-gray-500"}`} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-700">写作专家</span>
                    <span className="text-[8px] text-gray-400 max-w-[85px] truncate">综合提炼并生成文本</span>
                  </div>

                </div>
              </div>
            )}

            {/* LOGS MONITOR (TOP FLOATING BAR DURING CALCULATION) */}
            {progressLogs.length > 0 && (
              <div className="p-6 bg-slate-900 text-[#38BDF8] font-mono text-xs border-b border-slate-900 shrink-0 select-none max-h-40 overflow-y-auto space-y-1">
                <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-1.5 mb-2 font-sans select-none">
                  <span>⚙️ 控制台计算进程日志</span>
                  <span>线程状态: LATEST</span>
                </div>
                
                {progressLogs.map((log, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 leading-relaxed">
                    <span className="text-slate-600 font-sans">{idx + 1}.</span>
                    <span>{log}</span>
                  </div>
                ))}
                <div ref={logBoxEndRef} />
              </div>
            )}

            {/* RESULTS CONTENT RENDERER */}
            <div className="flex-1 overflow-y-auto p-10 relative">
              
              {!currentMarkdown && !isLoading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center select-none">
                  <div className="p-4 bg-indigo-50 text-indigo-600 rounded-3xl border border-indigo-100/60 mb-4 animate-bounce">
                    <Sparkles className="w-8 h-8 fill-indigo-200" />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-800 mb-1 font-sans">
                    高维度研讨空载中
                  </h3>
                  <p className="text-xs text-gray-400 max-w-[340px] leading-relaxed font-sans mt-0.5">
                    请在左侧配置相应的技术参数或论文要求，点击【运行】即可通过大模型生成完备的学术分析，或在左侧列表载入已有快照内容。
                  </p>
                </div>
              )}

              {/* Progress skeleton pulse loader */}
              {isLoading && !currentMarkdown && (
                <div className="space-y-6 animate-pulse select-none">
                  <div className="h-4 bg-gray-100 rounded-md w-1/3"></div>
                  <div className="space-y-3">
                    <div className="h-3 bg-gray-100 rounded-md w-full"></div>
                    <div className="h-3 bg-gray-100 rounded-md w-5/6"></div>
                    <div className="h-3 bg-gray-100 rounded-md w-11/12"></div>
                  </div>
                  <div className="h-24 bg-gray-50 border border-dashed rounded-2xl w-full flex items-center justify-center text-xs text-gray-400 font-sans">
                    正在实时转义流，加载大模型深度学术分析...
                  </div>
                  <div className="h-4 bg-gray-100 rounded-md w-1/4"></div>
                  <div className="space-y-3">
                    <div className="h-3 bg-gray-100 rounded-md w-full"></div>
                    <div className="h-3 bg-gray-100 rounded-md w-2/3"></div>
                  </div>
                </div>
              )}

              {/* Live dialogues display for multi-agent model chats */}
              {agentExchanges.length > 0 && (
                <div className="mb-8 space-y-4">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest border-b pb-2 mb-4">
                    智能体实时博弈交互记录
                  </h3>
                  
                  {agentExchanges.map((exchangeMsg, eIdx) => (
                    <div
                      key={eIdx}
                      className={`p-4 rounded-2xl border flex flex-col gap-1.5 transition-all hover:shadow-xs ${
                        exchangeMsg.agent.includes("搜索专家")
                          ? "bg-blue-50/20 border-blue-100/60 pl-5 border-l-4 border-l-blue-500"
                          : exchangeMsg.agent.includes("分析助手")
                          ? "bg-amber-50/20 border-amber-100/60 pl-5 border-l-4 border-l-amber-500"
                          : "bg-emerald-50/20 border-emerald-100/60 pl-5 border-l-4 border-l-emerald-500"
                      }`}
                    >
                      <span className={`text-[10px] font-bold tracking-wide uppercase ${
                        exchangeMsg.agent.includes("搜索专家")
                          ? "text-blue-600"
                          : exchangeMsg.agent.includes("分析助手")
                          ? "text-amber-600"
                          : "text-emerald-600"
                      }`}>
                        {exchangeMsg.agent}
                      </span>
                      <p className="text-xs text-gray-600 leading-relaxed font-sans">{exchangeMsg.message}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Render computed/stored content */}
              {currentMarkdown && (
                <div className="relative">
                  {/* Floating click copy action button */}
                  <div className="absolute top-0 right-0 z-10 select-none">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(currentMarkdown);
                        showToast("内容已复制到剪贴板！");
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-bold text-gray-400 hover:text-indigo-600 bg-gray-50 hover:bg-indigo-50 border hover:border-indigo-100 rounded-xl transition-all shadow-xs"
                      title="快速一键复制生成内容"
                    >
                      <span>一键复制 Markdown</span>
                    </button>
                  </div>

                  <div className="prose max-w-none">
                    <MarkdownRenderer text={currentMarkdown} />
                  </div>
                  {currentMarkdown && !isLoading && (
                    <button onClick={() => { const blob = new Blob([currentMarkdown], {type:'text/markdown'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `cs599_output_${Date.now()}.md`; a.click(); URL.revokeObjectURL(url); }} className="w-full py-3 rounded-full text-xs font-bold text-center text-white tracking-wide bg-slate-900 hover:bg-slate-800 transition-all shadow-md mt-4">
                      ⬇️ 下载结果 .md
                    </button>
                  )}
                </div>
              )}

            </div>

            {/* Quick Actions Footer bar */}
            {currentMarkdown && (
              <div className="h-14 px-8 bg-slate-50 border-t border-gray-100 flex items-center justify-between select-none shrink-0 text-[10px] text-gray-400 font-mono">
                <span>字符数统计: {currentMarkdown.length}</span>
              </div>
            )}

          </div>

        </section>

      </main>

      </div>
    </div>
  );
}
