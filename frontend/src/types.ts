export type Tab =
  | "assistant"
  | "report"
  | "outline"
  | "thesis"
  | "review"
  | "agents"
  | "skills"
  | "history"
  | "providers"
  | "settings"
  | "knowledge";

export interface HistoryItem {
  id: string;
  timestamp: string;
  type: string; // e.g., "智能助手", "研究报告", "大纲生成", "学术论文", "综述写作", "多智能体协作"
  title: string;
  content: string;
}

export interface SkillItem {
  id: string;
  name: string;
  description: string;
  category: "检索" | "分析" | "写作" | "辅助";
  isActive: boolean;
}

export interface ProviderInfo {
  name: string;
  display_name: string;
  base_url: string;
  default_model: string;
  has_key: boolean;
  is_active: boolean;
}

export interface HistoryReport {
  id: string;
  mode: string;
  topic: string;
  display_name: string;
  time: string;
  has_sources: boolean;
}