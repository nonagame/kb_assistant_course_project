"""定义输入输出"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str
    mode: Literal["auto", "qa", "leave"] = "auto"
    session_id: str | None = None


class SourceItem(BaseModel):
    index: int
    source: str
    page: int | None = None
    visibility: str

class EvidenceAssessment(BaseModel):
    level: Literal["high", "medium", "low", "not_applicable"]
    matched_chunks: int = 0
    distinct_sources: int = 0
    top_relevance: float | None = None
    citation_valid: bool = False
    needs_human_review: bool = False
    reasons: list[str] = Field(default_factory=list)

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    route: str
    retrieval_status: str
    session_id: str
    active_route: str = ""
    leave_id: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    evidence_assessment: EvidenceAssessment | None = None

