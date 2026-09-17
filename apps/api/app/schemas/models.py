"""Pydantic schemas for ExitRadar API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str


class WorkspaceOut(BaseModel):
    id: str
    owner_id: str
    name: str
    plan: str
    created_at: Optional[str] = None


class ThesisCreate(BaseModel):
    workspace_id: str
    name: str
    natural_language: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None


class ThesisUpdate(BaseModel):
    name: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None


class ThesisOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    criteria: Dict[str, Any]
    strategy: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SearchJobCreate(BaseModel):
    thesis_id: str
    location: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=40)
    query_override: Optional[Dict[str, Any]] = None


class SearchJobOut(BaseModel):
    id: str
    thesis_id: str
    status: str
    query: Dict[str, Any]
    stats: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CompanyOut(BaseModel):
    id: str
    canonical_name: str
    domain: Optional[str] = None
    phone_norm: Optional[str] = None
    address: Optional[str] = None
    geo: Optional[Dict[str, Any]] = None
    industry: Optional[str] = None
    revenue_est: Optional[float] = None
    founded_year: Optional[int] = None
    workspace_id: Optional[str] = None


class EvidenceOut(BaseModel):
    id: str
    company_id: str
    source: str
    type: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    observed_at: Optional[str] = None
    confidence: float = 0.7


class SignalOut(BaseModel):
    id: str
    company_id: str
    signal_type: str
    value: Any = None
    confidence: float = 0.5
    first_observed_at: Optional[str] = None
    last_observed_at: Optional[str] = None


class OpportunityOut(BaseModel):
    id: str
    company_id: str
    thesis_id: str
    fit: Optional[float] = None
    seller: Optional[float] = None
    timing: Optional[float] = None
    access: Optional[float] = None
    competition: Optional[float] = None
    opportunity_score: float
    confidence: float = 0.5
    model_version: str
    explanation: Dict[str, Any] = Field(default_factory=dict)
    computed_at: Optional[str] = None
    company: Optional[CompanyOut] = None
    recommendation: Optional[Dict[str, Any]] = None


class RecommendationOut(BaseModel):
    id: str
    company_id: str
    thesis_id: str
    action: str
    priority: int
    reason: Optional[str] = None
    status: str
    model_version: str
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class CadenceOut(BaseModel):
    max_outreach_per_week: int = 5
    max_research_slots: int = 4


class CadenceUpdate(BaseModel):
    max_outreach_per_week: Optional[int] = Field(default=None, ge=1, le=20)
    max_research_slots: Optional[int] = Field(default=None, ge=0, le=20)


class BookOfWorkGenerate(BaseModel):
    force: bool = False
    with_brief: bool = False
    week: Optional[str] = None


class BookSlotComplete(BaseModel):
    outcome: Optional[str] = None
    notes: Optional[str] = None


class BookSlotSkip(BaseModel):
    notes: Optional[str] = None


class OutreachCreate(BaseModel):
    channel: str = "email"
    contact_id: Optional[str] = None
    thesis_id: Optional[str] = None


class OutreachOut(BaseModel):
    id: str
    company_id: str
    contact_id: Optional[str] = None
    channel: str
    subject: Optional[str] = None
    body: Optional[str] = None
    prompt_version: Optional[str] = None
    evidence_refs: List[Any] = Field(default_factory=list)
    created_at: Optional[str] = None


class PipelineUpdate(BaseModel):
    thesis_id: str
    stage: Optional[str] = None
    probability: Optional[float] = None
    notes: Optional[str] = None


class ActivityCreate(BaseModel):
    activity_type: str
    outcome: Optional[str] = None
    recommendation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExportCreate(BaseModel):
    workspace_id: str
    thesis_id: str
    format: str = "csv"


class CommandCenterOut(BaseModel):
    opportunity_count: int
    newly_actionable: int
    warming_targets: int
    top_opportunities: List[Dict[str, Any]]
    open_recommendations: List[Dict[str, Any]]
    thesis_id: Optional[str] = None
    book_of_work: Optional[Dict[str, Any]] = None
    book_metrics: Optional[Dict[str, Any]] = None