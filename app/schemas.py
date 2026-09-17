from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["supported", "conflicting", "unsupported", "uncertain"]


# ---- what the agent must return (structured output) --------------------------------
class DraftClaim(BaseModel):
    text: str = Field(description="The claim as it should read in the report.")
    value: Optional[str] = Field(default=None, description="Numeric value if any, e.g. '18'.")
    unit: Optional[str] = Field(default=None, description="Unit, e.g. 'people', 'sessions'.")
    period: Optional[str] = Field(default=None, description="Period, e.g. 'Q1 2026'.")
    evidence_ids: list[int] = Field(default_factory=list, description="IDs of evidence records backing this claim.")
    status: Status
    reasoning: str = Field(description="Why this status: which sources, which rule applied.")


class DraftSuggestion(BaseModel):
    question: str = Field(description="A follow-up question to ask the partner.")
    about_claim_index: Optional[int] = Field(
        default=None, description="Index into the claims list this question relates to, or null."
    )


class AgentDraft(BaseModel):
    claims: list[DraftClaim]
    suggestions: list[DraftSuggestion]


# ---- API response shapes -----------------------------------------------------------
class EvidenceOut(BaseModel):
    id: int
    role: str
    format: str
    excerpt: str
    simulated: bool


class AnnotationOut(BaseModel):
    id: int
    note: str


class ClaimOut(BaseModel):
    id: int
    text: str
    value: Optional[str]
    unit: Optional[str]
    period: Optional[str]
    status: Status
    reasoning: str
    evidence_ids: list[int]
    annotations: list[AnnotationOut]


class SuggestionOut(BaseModel):
    id: int
    question: str
    about_claim_id: Optional[int]
    officer_validated: str


class ReportOut(BaseModel):
    event_id: int
    title: str
    program: str
    period: str
    status: str
    claims: list[ClaimOut]
    suggestions: list[SuggestionOut]
    evidence: list[EvidenceOut]  # all source evidence, verbatim, for the bottom of the doc
    pdf_path: Optional[str]


class AnnotationIn(BaseModel):
    note: str


class SuggestionDecisionIn(BaseModel):
    decision: Literal["kept", "dismissed"]


class ReviseIn(BaseModel):
    instruction: str  # officer's note: what to modify / different suggestions / re-verify


class NewReportIn(BaseModel):
    role: str
    format: str
    text: str
    simulated: bool = False


class RevisionDecisionIn(BaseModel):
    decision: Literal["accept", "refuse"]
