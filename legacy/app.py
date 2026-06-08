#!/usr/bin/env python3
"""CS599 AI Research Assistant v3 - Redesigned UI matching mockups"""
import sys, os, traceback, json, subprocess, time, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime
from pathlib import Path

# ===== Page Config =====
st.set_page_config(
    page_title="CS599 智能研究助手",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== CSS - Dark sidebar + card layout matching mockups =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

/* Sidebar dark theme */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1f2e 0%, #162033 100%) !important;
    border-right: 1px solid #2a3142;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] { color: #e2e8f0; }

/* Mode buttons */
.mode-btn-active {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.4) !important;
}
.mode-btn {
    background: rgba(255,255,255,0.06) !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    font-weight: 400 !important;
}
.mode-btn:hover {
    background: rgba(255,255,255,0.12) !important;
}

/* Main content cards */
.card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 1px solid #d1d5db !important;
    padding: 0.75rem 1rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.4) !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    border-radius: 10px !important;
    border: 1px solid #d1d5db !important;
}

/* Provider card */
.provider-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
}
.provider-card:hover { border-color: #3b82f6; }

/* Agent cards for crew */
.agent-card {
    background: linear-gradient(135deg, #f0f7ff 0%, #e8f0fe 100%);
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}

/* History item */
.history-item {
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    margin-bottom: 0.25rem;
    cursor: pointer;
    font-size: 0.82rem;
}
.history-item:hover { background: rgba(255,255,255,0.08); }

/* Result card */
.result-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-top: 1rem;
}

/* Section title */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 0.5rem;
}

/* Expander styling */
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
}

/* Stop button */
.stop-btn > button {
    background: #ef4444 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
}

/* Streamlit default fixes */
[data-testid="stVerticalBlock"] > [style*="flex"] > [style*="width"] {
    gap: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ===== Lazy imports =====
@st.cache_resource
def get_manager():
    from src.models.manager import get_model_manager
    return get_model_manager()

@st.cache_resource
def get_registry():
    from src.skills.registry import get_skill_registry
    return get_skill_registry()

# ===== Session State =====
def init_session():
    defaults = {
        "history": [], "current_result": None, "is_working": False,
        "selected_provider": "deepseek", "selected_model": "deepseek-chat",
        "selected_mode": "智能助手", "crew_result": None,
        "context_input": "", "context_source": "manual",
        "last_research": None, "workflow_mode": False,
        "uploaded_image": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ===== Report Persistence =====
REPORT_DIR = Path.home() / ".cs599-agent" / "reports"
REPORT_INDEX = REPORT_DIR / "index.json"


def _load_saved_reports() -> list:
    if REPORT_INDEX.exists():
        try:
            return json.loads(REPORT_INDEX.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _auto_name(mode: str, topic: str) -> str:
    """Auto-generate report name from topic."""
    if not topic or topic.strip() == "":
        return f"未命名任务"
    # Use first 20 chars of topic
    name = topic.strip()[:30]
    if len(topic) > 30:
        name += "..."
    return name


def save_report(mode: str, topic: str, content: str, sources: list = None):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_name = _auto_name(mode, topic)
    filename = f"{mode}_{ts}.md"
    filepath = REPORT_DIR / filename

    header = f"""# {display_name}

**模式**: {mode} | **时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | **主题**: {topic}

---

"""
    filepath.write_text(header + content, encoding="utf-8")

    reports = _load_saved_reports()
    reports.insert(0, {
        "id": ts, "mode": mode, "topic": topic,
        "display_name": display_name,
        "filename": filename, "filepath": str(filepath),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "has_sources": bool(sources),
    })
    reports = reports[:200]
    REPORT_INDEX.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(filepath)


def delete_report(report_id: str):
    reports = _load_saved_reports()
    for r in reports:
        if r["id"] == report_id:
            filepath = REPORT_DIR / r["filename"]
            if filepath.exists():
                filepath.unlink()
            reports = [x for x in reports if x["id"] != report_id]
            REPORT_INDEX.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
    return False


def load_report_content(report_id: str) -> str:
    """Load full content of a saved report."""
    reports = _load_saved_reports()
    for r in reports:
        if r["id"] == report_id:
            filepath = REPORT_DIR / r["filename"]
            if filepath.exists():
                return filepath.read_text(encoding="utf-8")
    return ""


# ===== Context Builder =====
def _context_selector(key_prefix: str) -> str:
    """Allow selecting manual context, history, or uploaded image."""
    ctx_tab1, ctx_tab2, ctx_tab3 = st.tabs(["📝 手动输入", "📚 历史记录", "🖼️ 图片上传"])

    context = ""

    with ctx_tab1:
        manual = st.text_area("上下文内容", height=80,
                               key=f"{key_prefix}_ctx_manual",
                               placeholder="提供背景信息或之前的内容...")
        if manual.strip():
            context = manual

    with ctx_tab2:
        reports = _load_saved_reports()
        if reports:
            opts = {r["id"]: f"[{r['mode']}] {r['display_name']}" for r in reports[:20]}
            sel = st.selectbox("选择历史记录", list(opts.keys()),
                               format_func=lambda x: opts[x],
                               key=f"{key_prefix}_ctx_hist")
            if sel:
                content = load_report_content(sel)
                # Strip header, keep body
                if "---" in content:
                    content = content.split("---", 1)[-1].strip()
                if st.button("📥 加载此记录", key=f"{key_prefix}_ctx_load"):
                    context = content[:5000]
                    st.success("已加载")
        else:
            st.caption("暂无历史记录")

    with ctx_tab3:
        img = st.file_uploader("上传图片（实验数据、图表等）", type=["png", "jpg", "jpeg"],
                               key=f"{key_prefix}_ctx_img")
        if img:
            st.session_state.uploaded_image = img
            st.image(img, width=200)
            context += "\n\n[用户上传了图片数据，请在分析中参考]"

    return context


# ===== Sidebar =====
def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1.5rem;">
            <span style="font-size:1.8rem;">🧠</span>
            <div>
                <span style="font-size:1.2rem;font-weight:700;color:#e2e8f0;">CS599</span>
                <span style="font-size:0.75rem;color:#94a3b8;margin-left:0.3rem;">v2.0</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Model Selection
        st.markdown("<p style='color:#94a3b8;font-size:0.75rem;margin-bottom:0.5rem;'>🤖 模型</p>", unsafe_allow_html=True)
        try:
            manager = get_manager()
            keyed = [p for p in manager.list_providers()
                     if manager.has_api_key(p.name) or p.name == "ollama"]
            names = [p.name for p in keyed] if keyed else []

            if names:
                if st.session_state.selected_provider not in names:
                    st.session_state.selected_provider = names[0]
                sel = st.selectbox("服务商", names,
                    index=names.index(st.session_state.selected_provider),
                    key="sb_provider",
                    on_change=lambda: _on_provider_change(names),
                    label_visibility="collapsed")
                st.session_state.selected_provider = sel

                # Model dropdown with fetch
                cache_key = f"cached_models_{sel}"
                model_list = st.session_state.get(cache_key, [])

                # Auto-populate with default model
                current_prov = next((p for p in keyed if p.name == sel), None)
                if current_prov and current_prov.default_model and current_prov.default_model not in model_list:
                    model_list.insert(0, current_prov.default_model)
                    st.session_state[cache_key] = model_list

                c1, c2 = st.columns([4, 1])
                with c1:
                    if model_list:
                        st.selectbox("模型", model_list,
                                     index=model_list.index(st.session_state.selected_model) if st.session_state.selected_model in model_list else 0,
                                     key="sb_model_select",
                                     on_change=lambda: st.session_state.update(selected_model=st.session_state.sb_model_select),
                                     label_visibility="collapsed")
                    else:
                        st.text_input("模型", value=st.session_state.selected_model, key="sb_model",
                                      label_visibility="collapsed")
                with c2:
                    if st.button("🔄", key=f"fetch_m_{sel}"):
                        with st.spinner(""):
                            try:
                                discovered = manager.discover_models(sel)
                                if discovered:
                                    st.session_state[cache_key] = [m.id for m in discovered]
                                    st.rerun()
                            except Exception:
                                st.toast("获取失败，使用默认模型")
            else:
                st.info("请配置服务商")
        except Exception as e:
            st.error(f"模型加载失败: {e}")

        st.divider()

        # History
        st.markdown("<p style='color:#94a3b8;font-size:0.75rem;margin-bottom:0.5rem;'>📚 历史记录</p>", unsafe_allow_html=True)
        reports = _load_saved_reports()
        if reports:
            for r in reports[:10]:
                # 防御：确保 key 存在（兼容旧格式数据）
                _disp = r.get('display_name', r.get('topic', '未命名任务'))[:18]
                _time = r.get('time', '')[:5]
                cols = st.columns([6, 1])
                with cols[0]:
                    label = f"<span style='color:#94a3b8;font-size:0.7rem;'>{_time}</span> <span style='color:#e2e8f0;'>{_disp}</span>"
                    st.markdown(label, unsafe_allow_html=True)
                with cols[1]:
                    if st.button("🗑️", key=f"del_r_{r['id']}", help="删除"):
                        delete_report(r['id']); st.rerun()
        else:
            st.caption("暂无记录")

        st.divider()

        # Mode Selection
        st.markdown("<p style='color:#94a3b8;font-size:0.75rem;margin-bottom:0.5rem;'>🎯 工作模式</p>", unsafe_allow_html=True)
        modes = [
            ("智能助手", "🤖"), ("调研报告", "🔍"), ("论文构思", "💡"),
            ("学术论文", "📄"), ("综述撰写", "📊"), ("智能体协作", "👥"),
            ("技能管理", "🧰"), ("服务商管理", "⚙️"),
        ]
        for mode, icon in modes:
            is_active = st.session_state.selected_mode == mode
            btn_type = "primary" if is_active else "secondary"
            css = "mode-btn-active" if is_active else "mode-btn"
            if st.button(f"{icon} {mode}", use_container_width=True, type=btn_type, key=f"mode_{mode}"):
                st.session_state.selected_mode = mode
                st.rerun()


def _on_provider_change(names):
    """Handle provider change: update model."""
    selected = st.session_state.sb_provider
    st.session_state.selected_provider = selected
    st.session_state.pop(f"cached_models_{selected}", None)
    try:
        manager = get_manager()
        for p in manager.list_providers():
            if p.name == selected and p.default_model:
                st.session_state.selected_model = p.default_model
                break
    except Exception:
        pass


# ===== Helpers =====
def check_key() -> bool:
    p = st.session_state.selected_provider
    if p == "ollama":
        return True
    try:
        if not get_manager().has_api_key(p):
            st.error("⚠️ 请先配置 API Key"); return False
    except Exception:
        return False
    return True


def run_skill(skill_name: str, topic: str, params: dict,
              skill_override: str = "", mcp_servers: list = None):
    if not topic:
        st.warning("请输入主题"); return
    if not check_key(): return

    # MCP pre-search
    if mcp_servers:
        try:
            from src.mcp.manager import get_mcp_manager
            mcp_mgr = get_mcp_manager()
            mcp_results = []
            for srv_name in mcp_servers:
                try:
                    result = mcp_mgr.call_tool(srv_name, "search", {
                        "query": topic, "max_results": 5,
                    })
                    if "error" not in result:
                        parsed = result.get("result", result.get("raw", []))
                        items = parsed.get("results", parsed) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                        for r in (items if isinstance(items, list) else [items]):
                            if isinstance(r, dict):
                                mcp_results.append(f"- {r.get('title', '')}: {r.get('content', r.get('snippet', ''))[:200]}")
                except Exception:
                    pass
            if mcp_results:
                params["context"] = params.get("context", "") + "\n\nMCP搜索结果：\n" + "\n".join(mcp_results[:10])
        except Exception:
            pass

    actual = skill_override if skill_override else skill_name
    st.session_state.is_working = True
    progress = st.progress(0)
    try:
        from src.skills.base import SkillContext
        progress.progress(0.2, text="执行中...")
        ctx = SkillContext(
            topic=topic, provider_name=st.session_state.selected_provider,
            model_id=st.session_state.selected_model, custom_params=params)
        progress.progress(0.5)
        result = get_registry().execute(actual, ctx)
        progress.progress(1.0)
        st.session_state.current_result = result

        # Save to history
        st.session_state.history.append({
            "mode": st.session_state.selected_mode, "topic": topic,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        # Auto-save report
        if hasattr(result, 'content') and result.content:
            save_report(st.session_state.selected_mode, topic, result.content,
                       getattr(result, 'sources', None))

        # Store research for workflow mode
        if st.session_state.selected_mode == "调研报告" and result.success:
            st.session_state.last_research = result.content

        if result.success:
            st.success("✅ 完成！")
        else:
            st.error(f"❌ {result.error}")
    except Exception as e:
        st.error(f"❌ 系统错误: {e}")
        with st.expander("调试"):
            st.code(traceback.format_exc())
    finally:
        st.session_state.is_working = False
        progress.empty()


def render_result():
    result = st.session_state.current_result
    if not result:
        return
    st.divider()
    if hasattr(result, 'success'):
        badge = "🟢 已完成" if result.success else "🔴 失败"
        st.markdown(f"**{badge}**")

    # Steps
    if hasattr(result, 'steps') and result.steps:
        with st.expander("🔄 执行步骤"):
            for step in result.steps:
                icon = {"done": "✅", "running": "🔄", "error": "❌"}.get(step.get("status", ""), "⏳")
                st.write(f"{icon} **{step.get('action', '')}**: {step.get('result', '')}")

    # Content
    if hasattr(result, 'content') and result.content:
        st.subheader("📄 结果")
        t1, t2 = st.tabs(["📖 预览", "📝 Markdown"])
        with t1:
            st.markdown(result.content)
        with t2:
            st.code(result.content, language="markdown")

        # Action buttons
        c1, c2 = st.columns([1, 1])
        with c1:
            fn = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            st.download_button("⬇️ 下载", result.content, fn, "text/markdown", use_container_width=True)
        with c2:
            if st.session_state.selected_mode == "调研报告" and result.success:
                if st.button("📄 基于调研生成论文", use_container_width=True):
                    st.session_state.workflow_mode = True
                    st.session_state.selected_mode = "学术论文"
                    st.rerun()

    # Sources
    if hasattr(result, 'sources') and result.sources:
        with st.expander(f"📚 参考来源 ({len(result.sources)})"):
            for s in result.sources[:20]:
                t, u = s.get("title", "?"), s.get("url", "")
                if u:
                    st.markdown(f"- [{t}]({u})")
                else:
                    st.write(f"- {t}")


# ===== Mode Renderers =====
def render_smart_assistant():
    st.markdown("## 🤖 智能助手")
    st.caption("输入任意需求，助手自动理解意图、调用技能和搜索工具完成")

    context = _context_selector("smart")
    if context:
        st.session_state.context_input = context

    query = st.text_area("你想做什么？", height=80, key="smart_q",
                         placeholder="如：帮我调研多智能体协作的最新进展并写一份综述")

    if st.button("🚀 执行", type="primary", disabled=st.session_state.is_working):
        if not query.strip():
            st.warning("请输入需求"); return
        if not check_key(): return
        st.session_state.is_working = True
        progress = st.progress(0)
        try:
            progress.progress(0.1, text="分析意图...")
            manager = get_manager()
            llm = manager.create_llm_client(st.session_state.selected_provider,
                                            st.session_state.selected_model, 0.3)
            ctx_block = f"\n上下文：{context}" if context else ""
            prompt = f"""分析用户需求，判断工具。可用工具：research/survey_writing/paper_writing/crew/chat。
用户输入：{query}{ctx_block}
只输出JSON：{{"tool": "...", "topic": "...", "reason": "..."}}"""
            resp = llm.invoke([{"role": "user", "content": prompt}])
            raw = resp.content if hasattr(resp, 'content') else str(resp)
            import re
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            decision = json.loads(m.group()) if m else {"tool": "chat", "topic": query}
            tool = decision.get("tool", "chat")
            topic = decision.get("topic", query)
            st.info(f"🔍 意图: **{tool}** | 主题: {topic}")

            if tool in ("research", "survey_writing", "paper_writing", "crew"):
                progress.progress(0.3, text="搜索信息...")
                from src.agent.tools import web_search, arxiv_search
                search_results = web_search(topic, max_results=5)
                arxiv_results = arxiv_search(topic, max_results=3)
                search_summary = ""
                if search_results or arxiv_results:
                    search_summary = "\n搜索结果：\n"
                    for s in (search_results + arxiv_results)[:8]:
                        search_summary += f"- [{s.title}]({s.url}): {s.snippet[:100]}...\n"
                if search_summary:
                    context = (context or "") + search_summary

            progress.progress(0.6, text=f"执行 {tool}...")
            if tool == "chat":
                chat_prompt = f"用户：{query}\n{ctx_block}\n请详细回答。"
                resp = llm.invoke([{"role": "user", "content": chat_prompt}])
                content = resp.content if hasattr(resp, 'content') else str(resp)
                st.session_state.current_result = type('R', (), {
                    'success': True, 'content': content,
                    'metadata': {"mode": "智能助手", "topic": query},
                    'steps': [{'action': '意图分析', 'status': 'done', 'result': tool},
                              {'action': '生成回答', 'status': 'done', 'result': '完成'}],
                    'sources': [], 'error': '', 'duration_ms': 0,
                })()
            elif tool == "crew":
                from src.crew.crew import Crew
                crew = Crew(provider_name=st.session_state.selected_provider,
                            model_id=st.session_state.selected_model)
                result = crew.run_sequential(topic, "report", 1)
                st.session_state.current_result = type('R', (), {
                    'success': result.get("success", False),
                    'content': result.get("document", ""),
                    'metadata': {"mode": "智能助手", "topic": topic},
                    'steps': [], 'sources': [], 'error': result.get("error", ""), 'duration_ms': 0,
                })()
            else:
                skill_map = {"research": "research", "survey_writing": "survey_writing",
                             "paper_writing": "paper_writing"}
                from src.skills.base import SkillContext
                ctx = SkillContext(topic=topic, provider_name=st.session_state.selected_provider,
                                   model_id=st.session_state.selected_model,
                                   custom_params={"depth": 3, "sources": ["web", "arxiv"],
                                                  "context": context or ""})
                st.session_state.current_result = get_registry().execute(skill_map.get(tool, "research"), ctx)

            progress.progress(1.0)
            st.success("✅ 完成！")
        except Exception as e:
            st.error(f"❌ 错误: {e}")
            with st.expander("调试"):
                st.code(traceback.format_exc())
        finally:
            st.session_state.is_working = False
            progress.empty()
    render_result()


def _tool_selector(default_skill: str = "", key_prefix: str = "") -> dict:
    """Render skill & MCP selection."""
    options = {}
    with st.expander("🔧 工具选项"):
        c1, c2 = st.columns(2)
        with c1:
            try:
                registry = get_registry()
                skills = registry.list_skills()
                skill_names = [s['name'] for s in skills]
                idx = skill_names.index(default_skill) if default_skill in skill_names else 0
                sel = st.selectbox("使用技能", skill_names, index=idx if skill_names else 0,
                                   format_func=lambda x: next((s['display_name'] for s in skills if s['name'] == x), x),
                                   key=f"{key_prefix}_sk")
                options['skill'] = sel
            except Exception:
                options['skill'] = ""
        with c2:
            try:
                from src.mcp.manager import get_mcp_manager
                mcp_mgr = get_mcp_manager()
                mcps = mcp_mgr.list_servers()
                active = [m.name for m in mcps if m.is_active]
                sel = st.multiselect("启用 MCP", active, default=active,
                                     format_func=lambda x: next((m.display_name for m in mcps if m.name == x), x),
                                     key=f"{key_prefix}_mc")
                options['mcp'] = sel
            except Exception:
                options['mcp'] = []
    return options


def render_research():
    st.markdown("## 🔍 研究报告")
    st.caption("深度研究任意主题，搜索网络与学术文献")

    context = _context_selector("r")
    tools = _tool_selector(default_skill="research", key_prefix="r")

    c1, c2 = st.columns([3, 1])
    with c1:
        topic = st.text_input("研究主题", placeholder="如：大语言模型推理能力研究", key="r_t")
    with c2:
        depth = st.slider("深度", 1, 5, 3, key="r_d")
    sources = st.multiselect("数据来源", ["web", "arxiv"], default=["web", "arxiv"], key="r_s",
                             format_func=lambda x: "🌐 网络" if x == "web" else "📚 arXiv")

    if st.button("🚀 开始生成", type="primary", disabled=st.session_state.is_working, use_container_width=True):
        params = {"depth": depth, "sources": sources, "context": context}
        run_skill("research", topic, params,
                  skill_override=tools.get("skill", ""),
                  mcp_servers=tools.get("mcp", []))
    render_result()


def render_paper_idea():
    st.markdown("## 💡 论文构思")
    st.caption("先调研生成报告，再构思论文大纲、创新点和写作建议")

    context = _context_selector("pi")

    topic = st.text_input("论文主题", placeholder="如：基于多智能体协作的自动化文献调研系统", key="pi_t")
    c1, c2 = st.columns(2)
    with c1:
        paper_type = st.selectbox("论文类型", ["研究论文", "综述论文", "短论文"], key="pi_tp")
    with c2:
        field = st.text_input("研究领域", placeholder="如：自然语言处理", key="pi_f")

    if st.button("🚀 生成调研与构思", type="primary", disabled=st.session_state.is_working, use_container_width=True):
        if not check_key(): return
        st.session_state.is_working = True
        progress = st.progress(0)
        try:
            from src.skills.base import SkillContext
            progress.progress(0.2, text="调研中...")
            ctx = SkillContext(topic=topic, provider_name=st.session_state.selected_provider,
                               model_id=st.session_state.selected_model,
                               custom_params={"depth": 4, "sources": ["web", "arxiv"], "context": context})
            research_result = get_registry().execute("research", ctx)
            if not research_result.success:
                st.error(f"调研失败: {research_result.error}"); return
            progress.progress(0.6, text="构思中...")
            llm = get_manager().create_llm_client(st.session_state.selected_provider,
                                                   st.session_state.selected_model, 0.7)
            idea_prompt = f"""基于以下调研内容，为{paper_type}构思框架。
主题：{topic} | 领域：{field or "未指定"}
调研内容：{research_result.content[:3000]}
请用中文提供：一、选题价值 二、论文大纲 三、创新点 四、参考文献 五、写作建议"""
            response = llm.invoke([{"role": "user", "content": idea_prompt}])
            idea = response.content if hasattr(response, 'content') else str(response)
            full = f"# 📚 调研报告\n\n{research_result.content}\n\n---\n\n{idea}"
            st.session_state.current_result = type('R', (), {
                'success': True, 'content': full,
                'metadata': {"mode": "论文构思", "topic": topic},
                'steps': research_result.steps + [{"action": "论文构思", "status": "done", "result": "完成"}],
                'sources': research_result.sources, 'error': '', 'duration_ms': 0,
            })()
            st.success("✅ 完成！")
        except Exception as e:
            st.error(f"❌ {e}")
            with st.expander("调试"):
                st.code(traceback.format_exc())
        finally:
            st.session_state.is_working = False
            progress.empty()
    render_result()


def render_paper():
    st.markdown("## 📄 学术论文生成")
    st.caption("自动生成包含摘要、引言、相关工作、方法、实验、结论的完整学术论文")

    # Workflow mode: pre-fill from last research
    if st.session_state.workflow_mode and st.session_state.last_research:
        st.info("📋 已加载上次调研结果作为上下文")
        context = st.session_state.last_research[:3000]
        st.session_state.workflow_mode = False
    else:
        context = _context_selector("p")

    tools = _tool_selector(default_skill="paper_writing", key_prefix="p")

    topic = st.text_input("论文标题/主题", placeholder="如：大语言模型推理能力研究综述", key="p_t")
    c1, c2 = st.columns(2)
    with c1:
        pt = st.selectbox("类型", ["research", "survey", "short", "review"], key="p_tp",
            format_func=lambda x: {"research": "研究论文", "survey": "综述论文", "short": "短论文", "review": "评论"}.get(x, x))
    with c2:
        style = st.selectbox("引用格式", ["academic", "ieee", "acm", "apa"], key="p_st",
                             format_func=lambda x: x.upper())
    length = st.select_slider("篇幅", ["short", "medium", "long"], key="p_ln",
                               format_func=lambda x: {"short": "精简", "medium": "适中", "long": "详细"}.get(x, x))
    if st.button("🚀 生成论文", type="primary", disabled=st.session_state.is_working, use_container_width=True):
        sections = ["abstract", "introduction", "related_work", "methodology", "experiments", "conclusion", "references"]
        params = {"paper_type": pt, "style": style, "length": length, "sections": sections, "context": context}
        run_skill("paper_writing", topic, params,
                  skill_override=tools.get("skill", ""),
                  mcp_servers=tools.get("mcp", []))
    render_result()


def render_survey():
    st.markdown("## 📊 综述撰写")
    st.caption("生成带有分类法和对比表的领域综述")

    context = _context_selector("s")
    tools = _tool_selector(default_skill="survey_writing", key_prefix="s")

    topic = st.text_input("综述主题", placeholder="如：多模态大语言模型", key="s_t")
    c1, c2 = st.columns(2)
    with c1:
        scope = st.selectbox("范围", ["focused", "broad", "comparative"], key="s_sc",
                             format_func=lambda x: {"focused": "聚焦", "broad": "广泛", "comparative": "对比"}.get(x, x))
    with c2:
        tax = st.checkbox("包含分类法", value=True, key="s_tx")
        comp = st.checkbox("包含对比表", value=True, key="s_cp")
    if st.button("🚀 生成综述", type="primary", disabled=st.session_state.is_working, use_container_width=True):
        params = {"scope": scope, "taxonomy": tax, "comparisons": comp, "context": context}
        run_skill("survey_writing", topic, params,
                  skill_override=tools.get("skill", ""),
                  mcp_servers=tools.get("mcp", []))
    render_result()


def render_crew():
    st.markdown("## 👥 多智能体协作")
    st.caption("搜索专家 + 分析助手 + 写作专家 协作完成")

    agents = [
        ("🔍 搜索专家", "负责检索和筛选相关文献资料"),
        ("🧠 分析助手", "负责数据分析和提炼关键信息"),
        ("✍️ 写作专家", "负责生成高质量的学术内容"),
    ]
    cols = st.columns(3)
    for i, (title, desc) in enumerate(agents):
        with cols[i]:
            st.markdown(f'<div class="agent-card"><h4>{title}</h4><p style="color:#64748b;font-size:0.85rem;">{desc}</p></div>', unsafe_allow_html=True)

    context = _context_selector("c")
    topic = st.text_input("任务主题", placeholder="让团队研究什么主题？", key="c_t")
    c1, c2 = st.columns(2)
    with c1:
        doc_type = st.selectbox("输出", ["report", "paper", "summary"], key="c_dt",
                                format_func=lambda x: {"report": "调研报告", "paper": "学术论文", "summary": "摘要"}.get(x, x))
    with c2:
        iterations = st.slider("审查轮数", 1, 3, 1, key="c_it")

    if st.button("🚀 启动协作", type="primary", disabled=st.session_state.is_working, use_container_width=True):
        if not check_key(): return
        st.session_state.is_working = True
        progress = st.progress(0)
        try:
            from src.crew.crew import Crew
            crew = Crew(provider_name=st.session_state.selected_provider,
                        model_id=st.session_state.selected_model)
            progress.progress(0.3, text="搜索专家调研中...")
            result = crew.run_sequential(topic, doc_type, iterations)
            progress.progress(1.0)
            st.session_state.current_result = type('R', (), {
                'success': result.get("success", False),
                'content': result.get("document", ""),
                'metadata': {"mode": "智能体协作"}, 'steps': [], 'sources': [],
                'error': result.get("error", ""), 'duration_ms': 0,
            })()
            if result.get("success"):
                st.success("✅ 协作完成！")
            else:
                st.error(f"❌ {result.get('error', '未知错误')}")
        except Exception as e:
            st.error(f"❌ {e}")
            with st.expander("调试"):
                st.code(traceback.format_exc())
        finally:
            st.session_state.is_working = False
            progress.empty()
    if st.session_state.crew_result:
        with st.expander("📋 协作日志"):
            for entry in st.session_state.crew_result.get("workflow_log", []):
                emoji = {"phase": "🔄", "complete": "✅", "decision": "🤔", "error": "❌"}.get(entry.get("type", ""), "•")
                st.write(f"{emoji} **{entry.get('agent', '')}**: {entry.get('message', '')}")
    render_result()


def render_skills():
    st.markdown("## 🧰 技能管理")

    with st.expander("➕ 安装新技能"):
        st.caption("支持：Python代码 / .py文件 / .zip技能包")
        tab1, tab2, tab3 = st.tabs(["📝 粘贴代码", "📁 上传文件", "📦 上传技能包"])
        with tab1:
            code = st.text_area("Python代码", height=200, key="sk_c",
                                placeholder='from src.skills.base import BaseSkill, SkillResult...')
            fn = st.text_input("文件名", value="my_skill.py", key="sk_fn")
            if st.button("安装", key="sk_inst_c") and code.strip():
                try:
                    ok, msg = get_registry().install_from_code(code, fn)
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()
                except Exception as e:
                    st.error(f"失败: {e}")
        with tab2:
            up = st.file_uploader("选择.py文件", type=["py"], key="sk_up")
            if up and st.button("安装", key="sk_inst_f"):
                import tempfile
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".py", delete=False) as tmp:
                    tmp.write(up.getvalue())
                    ok = get_registry().install_skill(Path(tmp.name))
                    st.success("安装成功") if ok else st.error("失败")
                    if ok: st.rerun()
        with tab3:
            st.caption("技能包：SKILL.md + scripts/ + requirements.txt + .py文件")
            zup = st.file_uploader("选择.zip技能包", type=["zip"], key="sk_zup")
            if zup and st.button("📦 安装技能包", key="sk_inst_z"):
                try:
                    import zipfile, tempfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zp = Path(tmpdir) / "s.zip"
                        zp.write_bytes(zup.getvalue())
                        ed = Path(tmpdir) / "e"
                        with zipfile.ZipFile(zp, 'r') as z:
                            z.extractall(ed)
                        # Install requirements
                        for req in ed.rglob("requirements.txt"):
                            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)],
                                          capture_output=True, text=True)
                        # Register skills
                        installed = 0
                        for pyf in ed.rglob("*.py"):
                            if pyf.name.startswith("__") or pyf.name.startswith("test_"):
                                continue
                            if get_registry().install_skill(pyf):
                                installed += 1
                        st.success(f"安装了 {installed} 个技能") if installed else st.error("未找到有效技能")
                        if installed: st.rerun()
                except Exception as e:
                    st.error(f"失败: {e}")

    st.divider()
    try:
        registry = get_registry()
        skills = registry.list_skills()
        st.caption(f"共 {len(skills)} 个技能")
        for s in skills:
            source = registry.get_skill_source(s['name'])
            is_user = source == 'user'
            badge = "🟢 用户" if is_user else "⚪ 内置"
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f"**{s['display_name']}** `{s['name']}` <span style='font-size:0.7rem;color:#999;'>{badge}</span>", unsafe_allow_html=True)
                st.caption(s['description'])
            with c2:
                if is_user and st.button("🗑️", key=f"dsk_{s['name']}"):
                    ok, msg = registry.uninstall_skill(s['name'])
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()
    except Exception as e:
        st.error(f"加载失败: {e}")


def render_provider_mgmt():
    st.markdown("## ⚙️ 服务商管理")
    st.caption("管理 LLM 模型服务商、搜索工具和 MCP")
    manager = get_manager()

    # Providers - card layout
    st.markdown("### 🤖 LLM 服务商")
    for p in manager.list_providers():
        has_key = manager.has_api_key(p.name)
        can_del = p.name not in {"deepseek", "openai", "anthropic", "siliconflow",
                                  "openrouter", "dashscope", "kimi", "zhipu", "baidu", "ollama"}
        status = "🟢 已配置" if has_key else "⚪ 未配置"

        with st.container():
            st.markdown(f'<div class="provider-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(f"**{p.display_name}** `{p.name}`")
                st.caption(f"Base URL: `{p.base_url or '未配置'}` | 模型: `{p.default_model}`")
            with c2:
                st.write(f"{status}")
            with c3:
                if st.button("✏️ 编辑", key=f"ed_{p.name}"):
                    st.session_state[f"editing_{p.name}"] = True
                    st.rerun()
                if can_del and st.button("🗑️", key=f"dl_{p.name}"):
                    manager.remove_provider(p.name); st.rerun()

            # Edit form
            if st.session_state.get(f"editing_{p.name}", False):
                ec1, ec2 = st.columns(2)
                with ec1:
                    nu = st.text_input("Base URL", value=p.base_url, key=f"eu_{p.name}")
                    nm = st.text_input("默认模型", value=p.default_model, key=f"em_{p.name}")
                with ec2:
                    nk = st.text_input("API Key", type="password",
                                       value=manager.get_api_key(p.name) or "", key=f"ek_{p.name}")
                if st.button("💾 保存", key=f"es_{p.name}"):
                    manager.update_provider(p.name, base_url=nu, default_model=nm)
                    if nk: manager.set_api_key(p.name, nk)
                    st.session_state[f"editing_{p.name}"] = False
                    st.success("已保存"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Add Provider
    st.markdown("---")
    st.markdown("### ➕ 添加服务商")
    try:
        from src.models.provider import get_preset_list
        presets = get_preset_list()
        pnames = {p.name: f"{p.display_name}" for p in presets}
        chosen = st.selectbox("选择预设", list(pnames.keys()), format_func=lambda x: pnames[x], key="pr_s")
        preset = presets[list(pnames.keys()).index(chosen)]
        c1, c2 = st.columns([3, 1])
        with c1:
            cu = st.text_input("自定义 Base URL (可选)", placeholder=preset.base_url, key="pr_u")
        with c2:
            pk = st.text_input("API Key", type="password", key="pr_k")
        if st.button("添加", use_container_width=True, key="pr_add") and chosen:
            url = cu.strip() or preset.base_url
            ok, msg = manager.add_provider_from_preset(chosen, pk.strip(), custom_base_url=url)
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()
    except Exception as e:
        st.error(f"预设加载失败: {e}")

    # MCP Management
    st.markdown("---")
    st.markdown("### 🔌 MCP 管理")
    try:
        from src.mcp.manager import get_mcp_manager, BUILTIN_MCP_PRESETS
        mcp_mgr = get_mcp_manager()

        # Tavily embedded control
        with st.container():
            st.markdown("**🚀 Tavily MCP 本地服务器**")
            running = mcp_mgr.is_tavily_running()
            st.success("✅ 运行中") if running else st.info("⏹️ 未运行")
            tc1, tc2, tc3 = st.columns([2, 2, 1])
            with tc1:
                proxy = st.text_input("代理", value="http://localhost:7980", key="tav_px")
            with tc2:
                tkey = st.text_input("Tavily Key (可选)", type="password", key="tav_k")
            with tc3:
                st.write(""); st.write("")
                if running:
                    if st.button("⏹️ 停止", key="tav_sp"):
                        ok, msg = mcp_mgr.stop_tavily_server()
                        st.success(msg) if ok else st.error(msg); st.rerun()
                else:
                    if st.button("▶️ 启动", key="tav_st"):
                        with st.spinner("启动中..."):
                            ok, msg = mcp_mgr.start_tavily_server(tkey.strip(), proxy.strip())
                        st.success(msg) if ok else st.error(msg)
                        if ok and "tavily" not in [s.name for s in mcp_mgr.list_servers()]:
                            mcp_mgr.add_from_preset("tavily", custom_url=f"{proxy.strip().rstrip('/')}/sse")
                        st.rerun()

        # Remote MCP
        st.markdown("**🌐 远程 MCP**")
        st.caption("输入远程 MCP Server URL 和 API Key（支持 SSE 模式，走代理）")
        rm1, rm2 = st.columns([3, 2])
        with rm1:
            remote_url = st.text_input("MCP URL", placeholder="https://mcp.tavily.com/sse", key="rm_u")
        with rm2:
            remote_key = st.text_input("API Key", type="password", key="rm_k")
        if st.button("添加远程 MCP", use_container_width=True, key="rm_add"):
            if remote_url.strip():
                name = remote_url.strip().split("//")[-1].split("/")[0].replace(".", "_")
                ok, msg = mcp_mgr.add_custom(name, f"远程 {name}", remote_url.strip(),
                                              api_key=remote_key.strip(), tools_prefix="tavily_")
                st.success(msg) if ok else st.error(msg)
                if ok: st.rerun()

        # List MCP servers
        st.divider()
        for srv in mcp_mgr.list_servers():
            dot = "🟢" if srv.is_active else "⚪"
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"{dot} **{srv.display_name}** `{srv.name}`")
                    st.caption(f"URL: `{srv.url}` | 类型: `{srv.server_type}`")
                with c2:
                    healthy, msg = mcp_mgr.health_check(srv.name)
                    st.write(f"{'✅' if healthy else '❌'} {msg}")
                with c3:
                    label = "禁用" if srv.is_active else "启用"
                    if st.button(label, key=f"mc_tg_{srv.name}"):
                        mcp_mgr.toggle(srv.name); st.rerun()
                    if st.button("🗑️", key=f"mc_dl_{srv.name}"):
                        mcp_mgr.remove(srv.name); st.rerun()

    except Exception as e:
        st.error(f"MCP 管理加载失败: {e}")

    # Search API Keys
    st.markdown("---")
    st.markdown("### 🔍 搜索工具 API Key")
    from src.agent.tools import list_search_backends, set_search_api_key, _get_search_api_key
    for b in list_search_backends():
        with st.container():
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**{b['display_name']}**")
                st.caption(b['description'])
            with c2:
                cur = _get_search_api_key(b['name']) or ""
                ki = st.text_input("Key", value=cur, type="password", key=f"sk_{b['name']}")
                if st.button("保存", key=f"sk_sv_{b['name']}"):
                    set_search_api_key(b['name'], ki.strip()); st.success("已保存")


# ===== Main =====
def main():
    init_session()
    render_sidebar()

    mode = st.session_state.selected_mode
    try:
        {
            "智能助手": render_smart_assistant,
            "调研报告": render_research,
            "论文构思": render_paper_idea,
            "学术论文": render_paper,
            "综述撰写": render_survey,
            "智能体协作": render_crew,
            "技能管理": render_skills,
            "服务商管理": render_provider_mgmt,
        }.get(mode, render_smart_assistant)()
    except Exception as e:
        st.error(f"页面渲染错误: {e}")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
