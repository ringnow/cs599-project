/** 通用 Tab 组件属性类型 */
import type { Tab } from "../types";

export interface TabProps {
  // Navigation
  activeTab: Tab;
  setActiveTab: (t: Tab) => void;

  // Loading / execution
  isLoading: boolean;
  progressLogs: string[];
  executionSteps: any[];
  currentMarkdown: string;
  logBoxEndRef: React.RefObject<HTMLDivElement | null>;

  // Providers
  selectedProvider: string;
  handleProviderChange: (name: string) => void;
  selectedModel: string;
  setSelectedModel: (m: string) => void;
  providersList: any[];
  sniffedModels: any[];

  // Context accordion
  contextText: string;
  setContextText: (v: string) => void;
  uploadedFiles: Array<{ name: string; size: string; content: string }>;
  setUploadedFiles: (fn: (prev: any[]) => any[]) => void;
  removeUploadedFile: (idx: number) => void;
  reportContext: string;
  setReportContext: (v: string) => void;
  reportFiles: Array<{ name: string; size: string; content: string }>;
  setReportFiles: (fn: (prev: any[]) => any[]) => void;
  removeReportFile: (idx: number) => void;
  outlineContext: string;
  setOutlineContext: (v: string) => void;
  outlineFiles: Array<{ name: string; size: string; content: string }>;
  setOutlineFiles: (fn: (prev: any[]) => any[]) => void;
  removeOutlineFile: (idx: number) => void;
  thesisContext: string;
  setThesisContext: (v: string) => void;
  thesisFiles: Array<{ name: string; size: string; content: string }>;
  setThesisFiles: (fn: (prev: any[]) => any[]) => void;
  removeThesisFile: (idx: number) => void;
  reviewContext: string;
  setReviewContext: (v: string) => void;
  reviewFiles: Array<{ name: string; size: string; content: string }>;
  setReviewFiles: (fn: (prev: any[]) => any[]) => void;
  removeReviewFile: (idx: number) => void;
  agentContext: string;
  setAgentContext: (v: string) => void;
  agentFiles: Array<{ name: string; size: string; content: string }>;
  setAgentFiles: (fn: (prev: any[]) => any[]) => void;
  removeAgentFile: (idx: number) => void;

  // Context accordion expansion
  isContextExpanded: boolean;
  setIsContextExpanded: (v: boolean) => void;
  reportContextExpanded: boolean;
  setReportContextExpanded: (v: boolean) => void;
  outlineContextExpanded: boolean;
  setOutlineContextExpanded: (v: boolean) => void;
  thesisContextExpanded: boolean;
  setThesisContextExpanded: (v: boolean) => void;
  reviewContextExpanded: boolean;
  setReviewContextExpanded: (v: boolean) => void;
  agentContextExpanded: boolean;
  setAgentContextExpanded: (v: boolean) => void;

  // History IDs
  selectedHistoryId: string;
  setSelectedHistoryId: (v: string) => void;
  reportHistoryId: string;
  setReportHistoryId: (v: string) => void;
  outlineHistoryId: string;
  setOutlineHistoryId: (v: string) => void;
  thesisHistoryId: string;
  setThesisHistoryId: (v: string) => void;
  reviewHistoryId: string;
  setReviewHistoryId: (v: string) => void;
  agentHistoryId: string;
  setAgentHistoryId: (v: string) => void;

  // History
  historyReports: any[];
  loadHistoryToContextTab: (id: string, setContext: any) => void;

  // Skills
  skillOverride: string;
  setSkillOverride: (v: string) => void;
  allSkills: any[];

  // MCP
  selectedMcpServers: string[];
  setSelectedMcpServers: (v: string[]) => void;

  // Report tab
  reportSubject: string;
  setReportSubject: (v: string) => void;
  reportField: string;
  setReportField: (v: string) => void;
  reportDepth: "基础" | "详细" | "专家";
  setReportDepth: (v: "基础" | "详细" | "专家") => void;
  includeCharts: boolean;
  setIncludeCharts: (v: boolean) => void;
  referenceCount: number;
  setReferenceCount: (v: number) => void;

  // Assistant tab
  assistantPrompt: string;
  setAssistantPrompt: (v: string) => void;

  // Outline tab
  outlineSubject: string;
  setOutlineSubject: (v: string) => void;
  outlineField: string;
  setOutlineField: (v: string) => void;
  outlinePaperType: string;
  setOutlinePaperType: (v: string) => void;

  // Thesis tab
  thesisBlock: string;
  setThesisBlock: (v: string) => void;
  thesisPrompt: string;
  setThesisPrompt: (v: string) => void;
  thesisStyle: string;
  setThesisStyle: (v: string) => void;
  thesisPaperType: string;
  setThesisPaperType: (v: string) => void;
  thesisLength: string;
  setThesisLength: (v: string) => void;

  // Review tab
  reviewKeyword: string;
  setReviewKeyword: (v: string) => void;
  reviewSourceCount: number;
  setReviewSourceCount: (v: number) => void;
  reviewScope: string;
  setReviewScope: (v: string) => void;
  reviewTaxonomy: boolean;
  setReviewTaxonomy: (v: boolean) => void;
  reviewComparisons: boolean;
  setReviewComparisons: (v: boolean) => void;

  // Agents tab
  agentTopic: string;
  setAgentTopic: (v: string) => void;
  agentDocType: string;
  setAgentDocType: (v: string) => void;
  agentIterations: number;
  setAgentIterations: (v: number) => void;
  agentExchanges: Array<{ agent: string; message: string }>;
  setAgentExchanges: (v: any[]) => void;

  // Skills tab
  skills: any[];
  rawSkills: any[];
  installCode: string;
  setInstallCode: (v: string) => void;
  installFilename: string;
  setInstallFilename: (v: string) => void;
  isInstallExpanded: boolean;
  setIsInstallExpanded: (v: boolean) => void;
  fetchSkills: () => void;
  installSkill: () => void;
  uninstallSkill: (name: string) => void;

  // Providers tab
  tavilyRunning: boolean;
  setTavilyRunning: (v: boolean) => void;
  mcpServers: any[];
  setMcpServers: (v: any[]) => void;
  filesystemRunning: boolean;
  memoryRunning: boolean;
  setSearchBackends: (v: any[]) => void;
  searchBackends: any[];
  editingProvider: string | null;
  setEditingProvider: (v: string | null) => void;
  editBaseUrl: string;
  setEditBaseUrl: (v: string) => void;
  editModel: string;
  setEditModel: (v: string) => void;
  editApiKey: string;
  setEditApiKey: (v: string) => void;
  addPresetName: string;
  setAddPresetName: (v: string) => void;
  addCustomUrl: string;
  setAddCustomUrl: (v: string) => void;
  addApiKey: string;
  setAddApiKey: (v: string) => void;
  tavilyKey: string;
  setTavilyKey: (v: string) => void;
  tavilyProxy: string;
  setTavilyProxy: (v: string) => void;
  remoteMcpUrl: string;
  setRemoteMcpUrl: (v: string) => void;
  remoteMcpKey: string;
  setRemoteMcpKey: (v: string) => void;
  braveSearchKey: string;
  setBraveSearchKey: (v: string) => void;
  bochaSearchKey: string;
  setBochaSearchKey: (v: string) => void;
  semanticScholarKey: string;
  setSemanticScholarKey: (v: string) => void;
  showCustomProvider: boolean;
  setShowCustomProvider: (v: boolean) => void;
  customProviderName: string;
  setCustomProviderName: (v: string) => void;
  customProviderUrl: string;
  setCustomProviderUrl: (v: string) => void;
  customProviderKey: string;
  setCustomProviderKey: (v: string) => void;
  customProviderModel: string;
  setCustomProviderModel: (v: string) => void;

  // Providers tab actions
  startTavily: () => void;
  stopTavily: () => void;
  startStdioMcp: (name: string) => void;
  stopStdioMcp: (name: string) => void;
  addRemoteMcp: () => void;
  toggleMcp: (name: string) => void;
  deleteMcp: (name: string) => void;
  startEdit: (p: any) => void;
  saveEdit: (name: string) => void;
  deleteProvider: (name: string) => void;
  sniffModels: (name: string) => void;
  addProvider: () => void;
  addCustomProviderFn: () => void;
  saveSearchKey: (name: string, key: string) => void;
  refreshAll: () => void;
  fetchSkills: () => void;
  fetchTavilyStatus: () => void;
  fetchMcpServers: () => void;
  fetchProviders: () => void;
  fetchPresets: () => void;
  fetchStdioStatus: () => void;
  presetsList: any[];
  showToast: (msg: string) => void;

  // Settings tab
  latexEnabled: boolean;
  setLatexEnabled: (v: boolean) => void;
  persistEnabled: boolean;
  setPersistEnabled: (v: boolean) => void;

  // Execution
  handleRunTask: (taskType: Tab) => void;
}