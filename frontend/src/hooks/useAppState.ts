/** useAppState — 集中管理所有 App 状态变量 */
import { useState, useRef } from "react";
import { Tab, HistoryItem, SkillItem } from "../types";

export interface AppState {
  // Navigation
  activeTab: Tab; setActiveTab: (t: Tab) => void;
  apiUrl: string; setApiUrl: (v: string) => void;
  apiKey: string; setApiKey: (v: string) => void;
  selectedModel: string; setSelectedModel: (v: string) => void;
  selectedProvider: string; setSelectedProvider: (v: string) => void;

  // History
  history: HistoryItem[]; setHistory: (v: HistoryItem[]) => void;
  historyReports: any[]; setHistoryReports: (v: any[]) => void;
  selectedHistoryId: string; setSelectedHistoryId: (v: string) => void;

  // Context accordion (assistant tab)
  isContextExpanded: boolean; setIsContextExpanded: (v: boolean) => void;
  contextText: string; setContextText: (v: string) => void;
  uploadedFiles: any[]; setUploadedFiles: (fn: any) => void;

  // Per-tab contexts
  reportContext: string; setReportContext: (v: string) => void;
  reportFiles: any[]; setReportFiles: (fn: any) => void;
  reportContextExpanded: boolean; setReportContextExpanded: (v: boolean) => void;
  outlineContext: string; setOutlineContext: (v: string) => void;
  outlineFiles: any[]; setOutlineFiles: (fn: any) => void;
  outlineContextExpanded: boolean; setOutlineContextExpanded: (v: boolean) => void;
  thesisContext: string; setThesisContext: (v: string) => void;
  thesisFiles: any[]; setThesisFiles: (fn: any) => void;
  thesisContextExpanded: boolean; setThesisContextExpanded: (v: boolean) => void;
  reviewContext: string; setReviewContext: (v: string) => void;
  reviewFiles: any[]; setReviewFiles: (fn: any) => void;
  reviewContextExpanded: boolean; setReviewContextExpanded: (v: boolean) => void;
  agentContext: string; setAgentContext: (v: string) => void;
  agentFiles: any[]; setAgentFiles: (fn: any) => void;
  agentContextExpanded: boolean; setAgentContextExpanded: (v: boolean) => void;

  // History IDs per tab
  reportHistoryId: string; setReportHistoryId: (v: string) => void;
  outlineHistoryId: string; setOutlineHistoryId: (v: string) => void;
  thesisHistoryId: string; setThesisHistoryId: (v: string) => void;
  reviewHistoryId: string; setReviewHistoryId: (v: string) => void;
  agentHistoryId: string; setAgentHistoryId: (v: string) => void;

  // Providers
  providersList: any[]; setProvidersList: (v: any[]) => void;
  providersHealth: Record<string, any>; setProvidersHealth: (v: any) => void;
  presetsList: any[]; setPresetsList: (v: any[]) => void;
  backendOnline: boolean; setBackendOnline: (v: boolean) => void;
  sniffedModels: any[]; setSniffedModels: (v: any[]) => void;

  // Custom provider
  customProviderName: string; setCustomProviderName: (v: string) => void;
  customProviderUrl: string; setCustomProviderUrl: (v: string) => void;
  customProviderKey: string; setCustomProviderKey: (v: string) => void;
  customProviderModel: string; setCustomProviderModel: (v: string) => void;
  showCustomProvider: boolean; setShowCustomProvider: (v: boolean) => void;

  // Form states
  assistantPrompt: string; setAssistantPrompt: (v: string) => void;
  reportSubject: string; setReportSubject: (v: string) => void;
  reportField: string; setReportField: (v: string) => void;
  reportDepth: "基础" | "详细" | "专家"; setReportDepth: (v: "基础" | "详细" | "专家") => void;
  includeCharts: boolean; setIncludeCharts: (v: boolean) => void;
  referenceCount: number; setReferenceCount: (v: number) => void;
  outlineSubject: string; setOutlineSubject: (v: string) => void;
  outlineField: string; setOutlineField: (v: string) => void;
  thesisBlock: string; setThesisBlock: (v: string) => void;
  thesisPrompt: string; setThesisPrompt: (v: string) => void;
  thesisStyle: string; setThesisStyle: (v: string) => void;
  reviewKeyword: string; setReviewKeyword: (v: string) => void;
  reviewSourceCount: number; setReviewSourceCount: (v: number) => void;
  agentTopic: string; setAgentTopic: (v: string) => void;
  agentExchanges: any[]; setAgentExchanges: (v: any[]) => void;

  // Extra form params
  outlinePaperType: string; setOutlinePaperType: (v: string) => void;
  thesisPaperType: string; setThesisPaperType: (v: string) => void;
  thesisLength: string; setThesisLength: (v: string) => void;
  reviewScope: string; setReviewScope: (v: string) => void;
  reviewTaxonomy: boolean; setReviewTaxonomy: (v: boolean) => void;
  reviewComparisons: boolean; setReviewComparisons: (v: boolean) => void;
  agentDocType: string; setAgentDocType: (v: string) => void;
  agentIterations: number; setAgentIterations: (v: number) => void;

  // Execution
  isLoading: boolean; setIsLoading: (v: boolean) => void;
  progressLogs: string[]; setProgressLogs: (v: any) => void;
  executionSteps: any[]; setExecutionSteps: (v: any[]) => void;
  currentMarkdown: string; setCurrentMarkdown: (v: string) => void;

  // Skills
  skills: SkillItem[]; setSkills: (fn: any) => void;
  rawSkills: any[]; setRawSkills: (v: any[]) => void;
  installCode: string; setInstallCode: (v: string) => void;
  installFilename: string; setInstallFilename: (v: string) => void;
  isInstallExpanded: boolean; setIsInstallExpanded: (v: boolean) => void;
  allSkills: any[]; setAllSkills: (v: any[]) => void;
  skillOverride: string; setSkillOverride: (v: string) => void;

  // MCP
  mcpServers: any[]; setMcpServers: (v: any[]) => void;
  selectedMcpServers: string[]; setSelectedMcpServers: (v: string[]) => void;
  tavilyRunning: boolean; setTavilyRunning: (v: boolean) => void;
  filesystemRunning: boolean; setFilesystemRunning: (v: boolean) => void;
  memoryRunning: boolean; setMemoryRunning: (v: boolean) => void;
  searchBackends: any[]; setSearchBackends: (v: any[]) => void;

  // Provider editing
  editingProvider: string | null; setEditingProvider: (v: string | null) => void;
  editBaseUrl: string; setEditBaseUrl: (v: string) => void;
  editModel: string; setEditModel: (v: string) => void;
  editApiKey: string; setEditApiKey: (v: string) => void;
  addPresetName: string; setAddPresetName: (v: string) => void;
  addCustomUrl: string; setAddCustomUrl: (v: string) => void;
  addApiKey: string; setAddApiKey: (v: string) => void;
  tavilyKey: string; setTavilyKey: (v: string) => void;
  tavilyProxy: string; setTavilyProxy: (v: string) => void;
  remoteMcpUrl: string; setRemoteMcpUrl: (v: string) => void;
  remoteMcpKey: string; setRemoteMcpKey: (v: string) => void;
  braveSearchKey: string; setBraveSearchKey: (v: string) => void;
  bochaSearchKey: string; setBochaSearchKey: (v: string) => void;
  semanticScholarKey: string; setSemanticScholarKey: (v: string) => void;

  // Settings
  latexEnabled: boolean; setLatexEnabled: (v: boolean) => void;
  persistEnabled: boolean; setPersistEnabled: (v: boolean) => void;

  // Toast
  toastMessage: string; setToastMessage: (v: string) => void;

  // Refs
  logBoxEndRef: React.RefObject<HTMLDivElement | null>;
  timerRefs: React.MutableRefObject<ReturnType<typeof setTimeout>[]>;
  abortControllerRef: React.MutableRefObject<AbortController | null>;
  currentRequestIdRef: React.MutableRefObject<string>;

  // Inline helpers
  clearAllTimers: () => void;
}

export function useAppState(): AppState {
  const [activeTab, setActiveTab] = useState<Tab>("assistant");
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem("cs599_api_url") || "");
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("cs599_api_key") || "");
  const [selectedModel, setSelectedModel] = useState("gemini-3.5-flash");
  const [selectedProvider, setSelectedProvider] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyReports, setHistoryReports] = useState<any[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState("");

  // Context (assistant)
  const [isContextExpanded, setIsContextExpanded] = useState(false);
  const [contextText, setContextText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);

  // Per-tab context
  const [reportContext, setReportContext] = useState("");
  const [reportFiles, setReportFiles] = useState<any[]>([]);
  const [reportContextExpanded, setReportContextExpanded] = useState(false);
  const [outlineContext, setOutlineContext] = useState("");
  const [outlineFiles, setOutlineFiles] = useState<any[]>([]);
  const [outlineContextExpanded, setOutlineContextExpanded] = useState(false);
  const [thesisContext, setThesisContext] = useState("");
  const [thesisFiles, setThesisFiles] = useState<any[]>([]);
  const [thesisContextExpanded, setThesisContextExpanded] = useState(false);
  const [reviewContext, setReviewContext] = useState("");
  const [reviewFiles, setReviewFiles] = useState<any[]>([]);
  const [reviewContextExpanded, setReviewContextExpanded] = useState(false);
  const [agentContext, setAgentContext] = useState("");
  const [agentFiles, setAgentFiles] = useState<any[]>([]);
  const [agentContextExpanded, setAgentContextExpanded] = useState(false);

  // History IDs
  const [reportHistoryId, setReportHistoryId] = useState("");
  const [outlineHistoryId, setOutlineHistoryId] = useState("");
  const [thesisHistoryId, setThesisHistoryId] = useState("");
  const [reviewHistoryId, setReviewHistoryId] = useState("");
  const [agentHistoryId, setAgentHistoryId] = useState("");

  // Providers
  const [providersList, setProvidersList] = useState<any[]>([]);
  const [providersHealth, setProvidersHealth] = useState<Record<string, any>>({});
  const [presetsList, setPresetsList] = useState<any[]>([]);
  const [backendOnline, setBackendOnline] = useState(true);
  const [sniffedModels, setSniffedModels] = useState<any[]>([]);

  // Custom provider
  const [customProviderName, setCustomProviderName] = useState("");
  const [customProviderUrl, setCustomProviderUrl] = useState("");
  const [customProviderKey, setCustomProviderKey] = useState("");
  const [customProviderModel, setCustomProviderModel] = useState("");
  const [showCustomProvider, setShowCustomProvider] = useState(false);

  // Form states
  const [assistantPrompt, setAssistantPrompt] = useState("帮助我研究多智能体协作的最新进展并写一份全面的总结。");
  const [reportSubject, setReportSubject] = useState("多智能体混合强化学习收敛性分析");
  const [reportField, setReportField] = useState("算网融合 / 理论决策控制");
  const [reportDepth, setReportDepth] = useState<"基础" | "详细" | "专家">("详细");
  const [includeCharts, setIncludeCharts] = useState(true);
  const [referenceCount, setReferenceCount] = useState(9);
  const [outlineSubject, setOutlineSubject] = useState("大语言模型智能体博弈与线性化控制");
  const [outlineField, setOutlineField] = useState("深度强化学习 / 自然语言处理");
  const [thesisBlock, setThesisBlock] = useState("第三章第一节：异步分布式节点损失界限证明");
  const [thesisPrompt, setThesisPrompt] = useState("提供详实的极限值不等式推导，包含收敛定理的Lipschitz常数L约束");
  const [thesisStyle, setThesisStyle] = useState("Nature标准格式");
  const [reviewKeyword, setReviewKeyword] = useState("Federated Multi-Agent Reinforcement Learning");
  const [reviewSourceCount, setReviewSourceCount] = useState(12);
  const [agentTopic, setAgentTopic] = useState("基于自适应对齐的有向图智能体协作");
  const [agentExchanges, setAgentExchanges] = useState<any[]>([]);

  // Extra form params
  const [outlinePaperType, setOutlinePaperType] = useState("研究论文");
  const [thesisPaperType, setThesisPaperType] = useState("research");
  const [thesisLength, setThesisLength] = useState("medium");
  const [reviewScope, setReviewScope] = useState("focused");
  const [reviewTaxonomy, setReviewTaxonomy] = useState(true);
  const [reviewComparisons, setReviewComparisons] = useState(true);
  const [agentDocType, setAgentDocType] = useState("report");
  const [agentIterations, setAgentIterations] = useState(1);

  // Execution
  const [isLoading, setIsLoading] = useState(false);
  const [progressLogs, setProgressLogs] = useState<string[]>([]);
  const [executionSteps, setExecutionSteps] = useState<any[]>([]);
  const [currentMarkdown, setCurrentMarkdown] = useState("");

  // Skills
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [rawSkills, setRawSkills] = useState<any[]>([]);
  const [installCode, setInstallCode] = useState("");
  const [installFilename, setInstallFilename] = useState("my_skill.py");
  const [isInstallExpanded, setIsInstallExpanded] = useState(false);
  const [allSkills, setAllSkills] = useState<any[]>([]);
  const [skillOverride, setSkillOverride] = useState("");

  // MCP
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [selectedMcpServers, setSelectedMcpServers] = useState<string[]>([]);
  const [tavilyRunning, setTavilyRunning] = useState(false);
  const [filesystemRunning, setFilesystemRunning] = useState(false);
  const [memoryRunning, setMemoryRunning] = useState(false);
  const [searchBackends, setSearchBackends] = useState<any[]>([]);

  // Provider editing
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

  // Settings
  const [latexEnabled, setLatexEnabled] = useState(() => localStorage.getItem("cs599_latex") !== "false");
  const [persistEnabled, setPersistEnabled] = useState(() => localStorage.getItem("cs599_persist") !== "false");

  // Toast
  const [toastMessage, setToastMessage] = useState("");

  // Refs
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

  return {
    activeTab, setActiveTab, apiUrl, setApiUrl, apiKey, setApiKey,
    selectedModel, setSelectedModel, selectedProvider, setSelectedProvider,
    history, setHistory, historyReports, setHistoryReports,
    selectedHistoryId, setSelectedHistoryId,
    isContextExpanded, setIsContextExpanded, contextText, setContextText,
    uploadedFiles, setUploadedFiles,
    reportContext, setReportContext, reportFiles, setReportFiles,
    reportContextExpanded, setReportContextExpanded,
    outlineContext, setOutlineContext, outlineFiles, setOutlineFiles,
    outlineContextExpanded, setOutlineContextExpanded,
    thesisContext, setThesisContext, thesisFiles, setThesisFiles,
    thesisContextExpanded, setThesisContextExpanded,
    reviewContext, setReviewContext, reviewFiles, setReviewFiles,
    reviewContextExpanded, setReviewContextExpanded,
    agentContext, setAgentContext, agentFiles, setAgentFiles,
    agentContextExpanded, setAgentContextExpanded,
    reportHistoryId, setReportHistoryId, outlineHistoryId, setOutlineHistoryId,
    thesisHistoryId, setThesisHistoryId, reviewHistoryId, setReviewHistoryId,
    agentHistoryId, setAgentHistoryId,
    providersList, setProvidersList, providersHealth, setProvidersHealth,
    presetsList, setPresetsList, backendOnline, setBackendOnline,
    sniffedModels, setSniffedModels,
    customProviderName, setCustomProviderName, customProviderUrl, setCustomProviderUrl,
    customProviderKey, setCustomProviderKey, customProviderModel, setCustomProviderModel,
    showCustomProvider, setShowCustomProvider,
    assistantPrompt, setAssistantPrompt,
    reportSubject, setReportSubject, reportField, setReportField,
    reportDepth, setReportDepth, includeCharts, setIncludeCharts,
    referenceCount, setReferenceCount,
    outlineSubject, setOutlineSubject, outlineField, setOutlineField,
    thesisBlock, setThesisBlock, thesisPrompt, setThesisPrompt,
    thesisStyle, setThesisStyle,
    reviewKeyword, setReviewKeyword, reviewSourceCount, setReviewSourceCount,
    agentTopic, setAgentTopic, agentExchanges, setAgentExchanges,
    outlinePaperType, setOutlinePaperType,
    thesisPaperType, setThesisPaperType, thesisLength, setThesisLength,
    reviewScope, setReviewScope, reviewTaxonomy, setReviewTaxonomy,
    reviewComparisons, setReviewComparisons,
    agentDocType, setAgentDocType, agentIterations, setAgentIterations,
    isLoading, setIsLoading, progressLogs, setProgressLogs,
    executionSteps, setExecutionSteps, currentMarkdown, setCurrentMarkdown,
    skills, setSkills, rawSkills, setRawSkills,
    installCode, setInstallCode, installFilename, setInstallFilename,
    isInstallExpanded, setIsInstallExpanded,
    allSkills, setAllSkills, skillOverride, setSkillOverride,
    mcpServers, setMcpServers, selectedMcpServers, setSelectedMcpServers,
    tavilyRunning, setTavilyRunning,
    filesystemRunning, setFilesystemRunning, memoryRunning, setMemoryRunning,
    searchBackends, setSearchBackends,
    editingProvider, setEditingProvider,
    editBaseUrl, setEditBaseUrl, editModel, setEditModel, editApiKey, setEditApiKey,
    addPresetName, setAddPresetName, addCustomUrl, setAddCustomUrl, addApiKey, setAddApiKey,
    tavilyKey, setTavilyKey, tavilyProxy, setTavilyProxy,
    remoteMcpUrl, setRemoteMcpUrl, remoteMcpKey, setRemoteMcpKey,
    braveSearchKey, setBraveSearchKey, bochaSearchKey, setBochaSearchKey,
    semanticScholarKey, setSemanticScholarKey,
    latexEnabled, setLatexEnabled, persistEnabled, setPersistEnabled,
    toastMessage, setToastMessage,
    logBoxEndRef, timerRefs, abortControllerRef, currentRequestIdRef,
    clearAllTimers,
  };
}
