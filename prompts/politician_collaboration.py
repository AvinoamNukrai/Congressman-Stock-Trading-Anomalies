"""Prompt + schema for pairwise legislative collaboration & overlap analysis (116th Congress)."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

COLLAB_PROMPT_TEMPLATE = """
ROLE:
You are a congressional legislative network analyst for the United States 116th Congress.

GOAL:
Given two member names, determine if they demonstrated meaningful legislative collaboration during the 116th Congress (window ending 2021-01-03) and list overlaps.

INPUT:
Politician A: {politician_a}
Politician B: {politician_b}

DEFINITIONS:
- legislative_collaboration: TRUE only if they co-sponsored, co-led, or jointly introduced at least one bill / resolution in the 116th Congress OR visibly coordinated on a public legislative initiative (hearings, amendments, marked reports). Otherwise FALSE.
- common_sponsorship_companies: Overlap of notable company / organization sponsorship or support entities tied to 2020 cycle. Names only, deduplicated. If unknown, return [].
- common_committees_116: Committees or subcommittees BOTH served on during the 116th; deduplicate. [] if none.

OUTPUT SCHEMA (JSON only):
{{
  "politician_1": "{politician_a}",
  "politician_2": "{politician_b}",
  "legislative_collaboration": true | false,
  "legislative_collaboration_evidence": "string or null",
  "common_sponsorship_companies": ["string", ...],
  "common_committees_116": ["string", ...]
}}

RULES:
- Return ONLY JSON.
- If setting legislative_collaboration true, evidence must cite at least one bill code, resolution number, hearing, or markup reference.
- Use null for evidence if FALSE.
- Deduplicate arrays case-insensitively, preserve first capitalization.
- If uncertain, default legislative_collaboration to false.
"""

def generate_collaboration_prompt(politician_a: str, politician_b: str) -> str:
    return COLLAB_PROMPT_TEMPLATE.format(politician_a=politician_a, politician_b=politician_b)


class PoliticianCollaboration(BaseModel):
    politician_1: str
    politician_2: str
    legislative_collaboration: bool
    legislative_collaboration_evidence: Optional[str]
    common_sponsorship_companies: List[str]
    common_committees_116: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "politician_1": "Jane Smith",
                "politician_2": "Alex Johnson",
                "legislative_collaboration": True,
                "legislative_collaboration_evidence": "Co-sponsored H.R.1234 and S.5678 joint initiative.",
                "common_sponsorship_companies": ["Microsoft", "Ford"],
                "common_committees_116": ["Committee on Energy and Commerce"]
            }
        }

__all__ = ["generate_collaboration_prompt", "PoliticianCollaboration"]

