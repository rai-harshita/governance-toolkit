from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SystemInfo(BaseModel):
    name: str
    version: str
    owner: str
    system_type: Literal["tabular_classifier", "genai_assistant"]
    intended_use: str
    out_of_scope: str


class Performance(BaseModel):
    accuracy: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    dataset_version: str


class SubgroupResult(BaseModel):
    attribute: str
    dp_difference: float = Field(ge=0, le=1)
    eo_difference: float = Field(ge=0, le=1)
    per_group: dict          # e.g. {"Male": {"selection_rate": 0.3}}
    group_sizes: dict        # e.g. {"Male": 14000, "Female": 7000}


class Explanation(BaseModel):
    method: str
    top_features: list[str]
    stability: float = Field(ge=-1, le=1)
    flagged_proxies: list[str] = []


class PromptRisks(BaseModel):
    injection_asr: float = Field(ge=0, le=1)
    jailbreak_asr: float = Field(ge=0, le=1)
    pii_leak_rate: float = Field(ge=0, le=1)
    over_refusal_rate: float = Field(ge=0, le=1)


class Decision(BaseModel):
    status: Literal["PASS", "CONDITIONAL", "BLOCK", "HUMAN_REVIEW"]
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    corrective_actions: list[str]
    evidence_run_id: str
    decided_at: datetime = Field(default_factory=datetime.now)


class GovernanceRecord(BaseModel):
    system: SystemInfo
    performance: Optional[Performance] = None
    subgroups: list[SubgroupResult] = []
    explanation: Optional[Explanation] = None
    limitations: list[str] = []
    assumptions: list[str] = []
    prompt_risks: Optional[PromptRisks] = None
    deployment_controls: dict = {}
    decision: Optional[Decision] = None