from pydantic import BaseModel
from typing import Optional, List


class AssistantRequest(BaseModel):
    prompt: str
    context: str = ""
    provider: str = ""
    model: str = ""
    mcp_servers: List[str] = []
    mcp_search_results: List[dict] = []
    request_id: str = ""


class ReportRequest(BaseModel):
    subject: str
    field: str = ""
    depth: str = "详细"
    includeCharts: bool = True
    referenceCount: int = 9
    context: str = ""
    skill_override: str = ""
    mcp_servers: List[str] = []
    provider: str = ""
    model: str = ""
    request_id: str = ""


class OutlineRequest(BaseModel):
    subject: str
    field: str = ""
    paper_type: str = "研究论文"
    context: str = ""
    skill_override: str = ""
    mcp_servers: List[str] = []
    provider: str = ""
    model: str = ""
    request_id: str = ""


class ThesisRequest(BaseModel):
    blockTitle: str
    prompt: str = ""
    style: str = "academic"
    paper_type: str = "research"
    length: str = "medium"
    sections: List[str] = []
    context: str = ""
    skill_override: str = ""
    mcp_servers: List[str] = []
    provider: str = ""
    model: str = ""
    request_id: str = ""


class ReviewRequest(BaseModel):
    keyword: str
    sourceCount: int = 12
    scope: str = "focused"
    taxonomy: bool = True
    comparisons: bool = True
    context: str = ""
    skill_override: str = ""
    mcp_servers: List[str] = []
    provider: str = ""
    model: str = ""
    request_id: str = ""


class AgentCollaborateRequest(BaseModel):
    topic: str
    doc_type: str = "report"
    iterations: int = 1
    context: str = ""
    skill_override: str = ""
    mcp_servers: List[str] = []
    provider: str = ""
    model: str = ""
    request_id: str = ""


class ApiResponse(BaseModel):
    logs: List[str] = []
    markdown: str = ""
    exchange: Optional[List[dict]] = None
    steps: List[dict] = []