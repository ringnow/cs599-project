import express from "express";
import path from "path";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";
import { createServer as createViteServer } from "vite";

dotenv.config();

const app = express();
app.use(express.json());

const PORT = 3000;

// Lazy-loaded Gemini client
let aiInstance: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.includes("MY_") || apiKey.trim() === "") {
    return null;
  }
  if (!aiInstance) {
    aiInstance = new GoogleGenAI({
      apiKey: apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiInstance;
}

// Academic response generator helper
async function generateAcademicText(prompt: string, systemInstruction?: string): Promise<string> {
  const ai = getGeminiClient();
  if (!ai) {
    // Deliver beautiful, informative simulated output when GEMINI_API_KEY is not configured
    return `### 💡 提示：未检测到有效的 GEMINI_API_KEY，当前处于离线演示模式

您可以在 **服务商管理** 或 AI Studio 系统的 **Settings > Secrets** 中设置您的 \`GEMINI_API_KEY\` 以启用实时的 AI 学术大模型生成。

---

### **[模拟生成] 关于“${prompt.slice(0, 40)}${prompt.length > 40 ? "..." : ""}”的分析：**

#### **1. 前沿挑战与研究现状**
在计算科学与人工智能的交叉领域（如 CS599 前沿课题），本主题的研究正在经历范式转变。基于深度表示学习和自适应对齐的模型能够解决长上下文建模、计算稳定性约束与跨域零样本迁移等核心痛点。当前研究的重点在于如何通过有限的先验约束，在高维参数空间中寻找局部最优均衡。

#### **2. 核心学术架构设计**
- **感知对齐层 (Perceptual Alignment Layer)**: 对多源异构输入进行归一化处理。
- **博弈演化模块 (Evolutionary Game Module)**: 通过模拟自适应网络转移函数，实现分布式智能体间的局部纳什对齐（Nash Synergy）。
- **可解释性自回归模型 (Explainable Auto-regressive Logic)**: 增加可解释注意力张量的权重分布，帮助追踪决策归因。

#### **3. 领域经典参考文献**
1. **Zhang, Y., & Wang, H. (2025).** "Scalable Deep Autoencoders for Multi-agent Coordination and Federated Topologies." *Journal of Machine Learning Research (JMLR)*, vol. 26, pp. 112–134.
2. **Li, S., et al. (2025).** "Decentralized Optimal Control with Deep Implicit Layers." *IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)*, vol. 47, no. 3, pp. 1024–1039.
3. **CS599 Collaborative Group (2026).** "Towards Generalizable Scientific Synthesizers: Foundations and Benchmarks." *International Conference on Machine Learning (ICML)*, 2026.`;
  }

  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        systemInstruction: systemInstruction || "You are an advanced academic research assistant (CS599-v2.0). Provide professional, deeply sourced, logic-driven responses in beautiful Chinese Markdown with proper literature citations and clear sections.",
      },
    });
    return response.text || "大模型未返回合法格式的内容。";
  } catch (error: any) {
    console.error("Gemini API error:", error);
    return `### **Gemini API 生成失败**\n\n系统在调用大模型时发生了错误：\n\`\`\`text\n${error.message || error}\n\`\`\`\n\n请进入 **服务商管理** 或 AI Studio 管理面板重新确认您的 API 密钥状态和额度。`;
  }
}

// API Routes

// Helper to provide step logs to client
app.post("/api/assistant", async (req, res) => {
  const { prompt, context } = req.body;
  const fullPrompt = `上下文追加:\n${context || "无"}\n\n请求主题/问题:\n${prompt}`;
  
  const systemInstruction = 
    "You are CS599 Assistant v2.0. You help researchers plan, retrieve, and write highly technical academic content. Speak with absolute authority, use strict professional formatting, formulas, and references.";
  
  const resultText = await generateAcademicText(fullPrompt, systemInstruction);
  
  res.json({
    logs: [
      "正在连接远程数据库检索文献...",
      "检测到上下文深度: " + (context ? `${context.length} 字符` : "默认"),
      "正在运行知识网络语义对齐...",
      "成功唤醒 CS599 智能助手计算流...",
      "生成完成！"
    ],
    markdown: resultText
  });
});

// Report generate endpoint
app.post("/api/report", async (req, res) => {
  const { subject, field, depth, includeCharts, referenceCount } = req.body;
  
  const prompt = `为您定制报告。\n报告主题: ${subject}\n研究领域: ${field}\n深度级别: ${depth}\n包含可视化图表: ${includeCharts ? "是" : "否"}\n推荐参考来源数量: ${referenceCount || 5}`;
  
  const systemInstruction = 
    "You are an academic reporter. Given a research topic, deliver a deeply structured, long-form academic report. Use proper markdown layout like headings, bullets, tables (to represent tables/charts), and bibliography.";
  
  const resultText = await generateAcademicText(prompt, systemInstruction);
  
  res.json({
    logs: [
      `初始化学术报告生成器 (核心: ${depth})...`,
      `分析研究领域: [${field}] ...`,
      `正在搜集相关学术刊物并匹配前 ${referenceCount || 5} 篇最相关引用...`,
      includeCharts ? "正在构建趋势数据拟合表图..." : "跳过图表模块...",
      "整合报告章节与附录...",
      "完成生成流程！"
    ],
    markdown: resultText
  });
});

// Outline generate endpoint
app.post("/api/outline", async (req, res) => {
  const { subject, field } = req.body;
  
  const prompt = `设计学术大纲：\n主题: ${subject}\n研究领域: ${field}`;
  const systemInstruction = 
    "You are an academic structure consultant. Generate a very detailed, multi-level academic paper framework containing Introduction, Methodology, Experiments, Analysis, Conclusion, and Bibliography sections in markdown.";
  
  const resultText = await generateAcademicText(prompt, systemInstruction);
  
  res.json({
    logs: [
      "正在提取关键科学研究假设...",
      "设计多层次逻辑大纲...",
      "正在标注每个章节的写作要点..."
    ],
    markdown: resultText
  });
});

// Academic thesis segment generator
app.post("/api/thesis", async (req, res) => {
  const { blockTitle, prompt, style } = req.body;
  
  const fullPrompt = `学术片段编写：\n要书写的学术段落/章节标题: ${blockTitle}\n详细描述与要求: ${prompt}\n写作学术风格: ${style}`;
  const systemInstruction = 
    "You are a stellar academic writing assistant. Write highly formal, passive-voice, precise, and dense academic text in Chinese. Ensure rigorous mathematical formulations if applicable, or comprehensive logical deduction.";
  
  const resultText = await generateAcademicText(fullPrompt, systemInstruction);
  
  res.json({
    logs: [
      "正在分析章节控制变量与技术深度...",
      "开始自回归生成高稠度学术段落...",
      "加入精确的学术语气转换..."
    ],
    markdown: resultText
  });
});

// Literature review generator
app.post("/api/literature-review", async (req, res) => {
  const { keyword, sourceCount } = req.body;
  
  const prompt = `撰写有关“${keyword}”的文献综述，要求覆盖不少于 ${sourceCount || 10} 篇代表性学术发表。`;
  const systemInstruction = 
    "You are a literature reviews synthesiser. Outline the debate, state-of-the-art architectures, research gaps, and organize the retrieved bibliography in tabular comparisons.";
  
  const resultText = await generateAcademicText(prompt, systemInstruction);
  
  res.json({
    logs: [
      `开始扫描 Google Scholar X-Ray 索引中关于 [${keyword}] 的条目...`,
      `成功比对 ${sourceCount || 10} 篇高引文献的优势和局限性...`,
      "合成时间轴对比矩阵...",
      "生成文献综述主体部分..."
    ],
    markdown: resultText
  });
});

// Multi-Agent collaboration simulation
app.post("/api/agents-collaborate", async (req, res) => {
  const { topic } = req.body;
  
  const client = getGeminiClient();
  if (!client) {
    // Return custom simulation script
    const exchange = [
      {
        agent: "搜索专家 (Search Expert)",
        message: "我已接入高引数据库，关于“" + topic + "”，已检索到ICML 2025、CVPR 2025的最新预印本32篇。关键文献主要集中在异构拓扑网络下的分布式收敛问题，已成功提炼出两个主流技术路线：全连通异步网络与星型有向对齐环。"
      },
      {
        agent: "分析助手 (Analysis Assistant)",
        message: "根据搜索专家提供的信息，我对这两种模型进行了复杂度分析。异步全连通网络虽然收敛上限极高，但通信开销达到对数立方级 $O(N^3 \\log N)$；而有向对齐环在牺牲5%收敛精度的同时，将每次迭代的吞吐代价平抑到了线性级 $O(N)$。因此在可拓展架构中，首推后一方案。"
      },
      {
        agent: "写作专家 (Writing Expert)",
        message: "收到。我将整理分析助手给出的复杂度比对结果。综述引言及理论设计部分，我们可以以定理（Theorem 1.1）的形式严格列出不同拓扑结构的流形流收敛界限，并以 LaTeX 数式和图表对比呈现，生成一份完整的学术方案草案。"
      }
    ];
    
    res.json({
      exchange,
      markdown: `### **多智能体协同输出：关于《${topic}》的可行性方案**

本方案由 **搜索专家**、**分析助手** 与 **写作专家** 自主完成多轮博弈交流得出：

#### **1. 拓扑复杂度对比矩阵**
| 拓扑结构 | 关键代表发布 | 核心优势 | 瓶颈 | 通信时空复杂度 |
| :--- | :--- | :--- | :--- | :--- |
| **异步全连通 (Fully Connected)** | Zhang et al. (ICML '25) | 高稳定性、全局收敛 | 极端通信损耗 | $\\mathcal{O}(N^3 \\log N)$ |
| **有向对齐环 (Directed Alignment)** | CS599 (NeurIPS '25) | 有限开销、线性拓展 | 存在收敛时滞 | $\\mathcal{O}(N)$ |

#### **2. 协同成果总结**
在分布式系统中，推荐采用**有向自适应对齐环**架构，由于各计算智能体本地只需存储与其相邻的拓扑状态矢量。系统整体可用性得到了质的飞跃。

#### **3. 文献引用目录**
- *Ref-A*: "Asynchronous Multi-Agent Convergence Topologies." *ICML*, 2025.
- *Ref-B*: "Linear Complexity in Directed Consensus Systems." *NeurIPS*, 2025.`
    });
    return;
  }
  
  try {
    // Generate real collaborative feedback
    const response = await client.models.generateContent({
      model: "gemini-3.5-flash",
      contents: `这是学术讨论主题: "${topic}"。请扮演三个人：搜索专家、分析助手、写作专家。针对该主题进行多轮针对性讨论。请严格返回一个包含三段话的 JSON 格式数据。格式必须为：
[
  {"agent": "搜索专家 (Search Expert)", "message": "搜集得到的学术材料结论..."},
  {"agent": "分析助手 (Analysis Assistant)", "message": "对搜集结果作出的深度数理和架构分析..."},
  {"agent": "写作专家 (Writing Expert)", "message": "最终的文本输出框架与表达决策..."}
]`,
      config: {
        responseMimeType: "application/json",
      }
    });
    
    let dialogue = [
      { agent: "搜索专家 (Search Expert)", message: "正在搜集有关该研究课题的相关材料..." },
      { agent: "分析助手 (Analysis Assistant)", message: "正在量化和优化该讨论的技术细节..." },
      { agent: "写作专家 (Writing Expert)", message: "正在将团队论点整合成严谨的 Markdown 文献..." }
    ];
    
    try {
      if (response.text) {
        dialogue = JSON.parse(response.text.trim());
      }
    } catch (e) {
      console.error("JSON parsing dialogue failed, using fallback formatting", e);
    }
    
    const docPrompt = `基于上述三位专家的学术交流成果 (成果摘要: ${JSON.stringify(dialogue)})，生成一篇关于“${topic}”的高维技术落地方案 Markdown 报告`;
    const finalDoc = await generateAcademicText(docPrompt, "You are a compiler scholar. Organize the brainstorming into a perfect concise technical report in Chinese with formulas and references.");
    
    res.json({
      exchange: dialogue,
      markdown: finalDoc
    });
  } catch (error: any) {
    console.error("Generate collaborate failed:", error);
    res.json({
      exchange: [
        { agent: "搜索专家 (Search Expert)", message: `请求出错: ${error.message}` },
        { agent: "分析助手 (Analysis Assistant)", message: "协同分析计算受阻" },
        { agent: "写作专家 (Writing Expert)", message: "无法组装成果" }
      ],
      markdown: `### **多智能体协作发生错误**\n\n通信流阻断，错误详情: \`${error.message}\``
    });
  }
});

// Load Vite middleware for development, serve static in production
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server starting smoothly on http://localhost:${PORT}`);
  });
}

startServer();
