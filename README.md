# CS599 智能研究助手 v2

**多模型 · 多智能体 · 技能系统**

Agentic AI 研究助手，支持多模型切换、多智能体协作和插件化技能系统，可生成调研报告、辅助论文构思、撰写学术论文。

方向一：Agentic AI 原生开发

[📹 点击观看 Demo 演示视频](https://github.com/ringnow/cs599-project/blob/main/vedio/output.mp4)

## v2 新特性

| 特性 | v1 | v2 |
|------|-----|-----|
| 模型支持 | 仅 DeepSeek | **任意 OpenAI 兼容 API + Ollama 本地模型** |
| 模型选择 | 固定 | **从 Base URL 自动发现** |
| 密钥存储 | .env 明文 | **AES-256 本地加密** |
| 智能体架构 | 单智能体 | **多智能体协作 (研究员+审查员+撰稿人)** |
| 论文构思 | 无 | **调研报告 → 论文大纲+创新点+写作建议** |
| 输出类型 | 调研报告 | **调研报告 / 论文构思 / 学术论文 / 综述** |
| 扩展性 | 固定 | **技能插件系统** |

## 技术栈

| 组件 | 技术 |
|------|------|
| 智能体框架 | LangGraph (ReAct) + CrewAI 模式 |
| 多模型管理 | 自定义 ModelManager（OpenAI 兼容） |
| 技能系统 | 插件化 Registry |
| 密钥安全 | cryptography (AES-128-CBC + PBKDF2) |
| 协议 | MCP (Model Context Protocol) |
| UI | React + Vite (原 Streamlit 已替换) |
| 学术搜索 | Semantic Scholar API + BoCha/Brave |
| 容器 | Docker + Docker Compose |
| AI IDE | claude code、kimi agent |

## 致谢

文献检索功能由 [Semantic Scholar](https://www.semanticscholar.org/) 提供支持。
PDF 解析由 [PyMuPDF](https://github.com/pymupdf/PyMuPDF) 提供支持。
免费 MCP 服务器由 [Model Context Protocol](https://github.com/modelcontextprotocol) 提供。

## 快速开始

### 1. 安装

```bash
git clone <你的仓库地址>
cd cs599-project
cp .env.example .env
pip install -r requirements.txt
# PDF 解析依赖（可选，用于读取论文全文）
pip install PyMuPDF
```

### 2. 配置 API 密钥

**方式一：Web 界面（推荐）**
- 启动应用后，在「服务商管理」中输入 API Key
- 密钥自动加密存储在 `~/.cs599-agent/`

**方式二：环境变量**
```bash
export DEEPSEEK_API_KEY=你的密钥
```

### 3. 启动

```bash
# 后端 API 服务（必需）
uvicorn src.api.server:app --reload --port 8000
# 打开 http://localhost:8000

# 前端开发（可选，用于前端开发调试）
cd frontend && npm install && npm run dev
# 打开 http://localhost:5173（自动代理 API 到 :8000）

# 旧版 Streamlit 界面（已废弃，由 React 前端替代）
# streamlit run src/app.py

# 命令行
python src/run_cli.py "研究主题" --skill research
python src/run_cli.py "论文主题" --skill paper_writing

# Docker
docker-compose up --build
```

## 核心功能

### 🔍 调研报告（学术级引用）
深度研究任意主题，支持：
- **论文深度阅读**：搜索到论文后自动下载 PDF / 调取 API 获取全文
- **LLM 评估**：逐篇评估论文关联度（高/中/低），只采纳"值得引用"的论文
- **真实引用**：正文使用 `[N]` 格式引用，参考文献仅含真实学术论文
- **排除非学术来源**：CSDN、知乎、博客园等不作为正式引用
- 参考文献格式规范：`作者. 标题 (年份). 期刊`

### 💡 论文构思
先进行深度调研生成报告，再基于报告为你构思：
- 选题价值分析
- 建议论文大纲
- 创新点建议
- 关键参考文献
- 写作建议

> 用户可以先生成调研报告，阅读后构思自己的论文，助手提供框架建议。

### 📄 学术论文
直接生成包含以下章节的完整学术论文：
- 摘要 (Abstract)
- 引言 (Introduction)
- 相关工作 (Related Work)
- 方法 (Methodology)
- 实验 (Experiments)
- 结论 (Conclusion)
- 参考文献 (References)

### 📊 综述撰写
生成带有分类法（Taxonomy）和对比表的领域综述文档。

### 👥 智能体协作
三个专业智能体协作完成任务：
1. **研究员** → 信息收集与分析
2. **审查员** → 质量检查与验证
3. **撰稿人** → 文档撰写与润色

### 🧰 技能管理
浏览和管理研究技能，支持安装自定义技能。**每个标签页（研究报告/大纲/论文/综述/智能助手/智能体）均可选择要执行的技能**。

### 🔌 免费 MCP 服务器
- **Filesystem MCP**：本地文件系统操作（免费，无需 API Key）
- **Memory MCP**：本地知识图谱记忆（免费，无需 API Key）
- **Tavily MCP**：AI 搜索引擎（需 Tavily API Key）

### 📊 后台步骤追踪
执行研究任务时，后台实时显示：
- ✅ 步骤状态（搜索/阅读/评估/合成/报告）
- 🔌 MCP 调用日志
- 📊 论文评估结果（关联度+是否引用）
- 📈 完整执行时间线

## 论文引用机制

```
搜索论文 → 下载PDF/API获取全文 → LLM逐篇评估 → 只保留值得引用的 → 正文编号引用 → 文末列出真实参考文献
```

- 搜索来源：Semantic Scholar（学术）+ BoCha/Brave（网络背景信息）
- 论文阅读：优先 OpenAccess PDF（PyMuPDF）→ 其次 S2 Paper API → 最后摘要
- 评估维度：核心发现、关联度（高/中/低）、是否值得引用
- 引用格式：`[N] 作者. 标题 (年份). 期刊. URL`
- 排除非学术来源：CSDN、知乎、博客园、个人主页等不作为正式引用

## MCP 服务器管理

通过「服务商管理」→「MCP 管理」面板可以：

| MCP 服务器 | 类型 | 费用 | 启动方式 |
|-----------|------|------|---------|
| Filesystem MCP | stdio | 免费 | 一键启动 |
| Memory MCP | stdio | 免费 | 一键启动 |
| Tavily Search (远程) | SSE | 需 API Key | 配置后启用 |
| 自定义 MCP | SSE | - | 手动添加 |

## 添加自定义模型

### 通过界面
1. 选择「自定义」服务商
2. 输入 Base URL（如 `https://api.example.com/v1`）
3. 点击「自动发现模型」或手动输入模型 ID
4. 保存 API 密钥

### 代码方式
```python
from src.models.manager import get_model_manager
from src.models.provider import ProviderConfig, ProviderType

manager = get_model_manager()
manager.add_provider(ProviderConfig(
    name="myprovider",
    display_name="我的服务商",
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.example.com/v1",
    default_model="gpt-4",
))
manager.set_api_key("myprovider", "你的密钥")
```

## 添加自定义技能

将 Python 文件放入 `skills_library/` 目录即可自动加载：

```python
# skills_library/my_skill.py
from src.skills.base import BaseSkill, SkillResult, SkillContext

class MySkill(BaseSkill):
    name = "my_skill"
    display_name = "我的技能"
    description = "描述"
    tags = ["custom", "research"]

    def execute(self, context: SkillContext) -> SkillResult:
        # 你的实现
        return SkillResult(success=True, content="结果")
```

## 目录结构

```
cs599-project/
├── src/                        # Python 后端
│   ├── api/                    # FastAPI REST API
│   │   ├── server.py           # 主服务入口
│   │   ├── schemas.py          # Pydantic 数据模型
│   │   ├── cancel.py           # 请求取消支持
│   │   └── routers/            # 路由模块
│   │       ├── agents.py       # 多智能体协作
│   │       ├── assistant.py    # 智能助手
│   │       ├── generation.py   # 报告/大纲/论文/综述生成
│   │       ├── history.py      # 历史记录（持久化存储）
│   │       ├── mcp.py          # MCP 协议
│   │       ├── providers.py    # 模型供应商管理
│   │       ├── search.py       # 搜索 API Key 管理
│   │       └── skills.py       # 技能管理
│   ├── models/                  # 多模型管理
│   │   ├── manager.py           # ModelManager
│   │   ├── provider.py          # Provider 配置 + 模型发现
│   │   └── key_store.py         # AES-256 加密存储
│   ├── skills/                  # 技能插件系统
│   │   ├── base.py              # BaseSkill
│   │   ├── registry.py          # 注册表
│   │   └── builtin/             # 内置技能
│   │       ├── research_skill.py
│   │       ├── paper_skill.py
│   │       ├── survey_skill.py
│   │       ├── code_review_skill.py
│   │       └── literature_review_skill.py
│   ├── crew/                    # 多智能体协作
│   │   ├── agent.py             # 智能体定义
│   │   └── crew.py              # 协调器
│   ├── agent/                   # 核心工具
│   │   ├── tools.py             # 搜索/提取工具
│   │   └── state.py             # 状态定义
│   ├── mcp/                     # MCP 协议管理
│   │   └── manager.py
│   ├── app.py                   # Streamlit 界面入口
│   ├── run_cli.py               # 命令行入口
│   ├── config.py                # 配置
│   └── requirements.txt         # Python 依赖
├── frontend/                    # React 前端 (Vite)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── types.ts
│   │   └── index.css
│   ├── server.ts                # Express 服务器 (Gemini)
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── skills_library/              # 用户自定义技能目录
├── docs/                        # 文档
│   ├── report.md                # 大作业报告
│   ├── ai-studio/               # Google AI Studio 配置
│   └── notes/                   # 开发笔记
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 密钥安全说明

API 密钥使用 **AES-256-CBC** 加密存储在 `~/.cs599-agent/api_keys.enc`：
- 加密密钥通过 PBKDF2 从机器标识（用户名+主机名）派生
- 换机器无法解密，防止密钥泄露
- 100,000 次 PBKDF2 迭代增加暴力破解成本

**切勿将密钥提交到 Git！** `.env` 和 `~/.cs599-agent/` 已加入 `.gitignore`。

## 许可证

MIT License（如为公开仓库）