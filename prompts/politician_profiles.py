"""Prompt + schema for extracting individual politician profile metadata for 116th Congress.

Produces one JSON object per politician with fields needed for the politician profile table.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

PROFILE_PROMPT_TEMPLATE = """
ROLE:
You are a senior political research analyst. You find, verify, and structure data about members of the United States 116th Congress with precise date bounds.

WINDOW:
Use data bounded to the 116th Congress service window ending 2021-01-03. Compute seniority relative to 2021-01-03. If unsure, set fields to null. Do not fabricate.

INPUT:
Target name (do NOT return it in output): {politician_name}

TASK:
Return ONLY valid JSON (no markdown, no commentary) matching the schema below for the provided target. Do NOT include the input name or any name field. Only return the requested attributes.

FIELD DEFINITIONS (ONLY THESE KEYS):
- sex: one of ["male","female","unknown"].
- party: party affiliation at 2019-01-03 (start of 116th); one of ["DEM","REP","IND","OTHER"] or null.
- birth_date: YYYY-MM-DD or null.
- state: state of official residence during 116th (e.g., "Washington", "Texas", etc.).
- city: primary residence city or null.
- university: name of highest degree institution, or null.
- seniority_in_congress_years: whole years served in Congress as of 2021-01-03, floor, or null.
- committees_116: list of full committee or subcommittee names (unique) served on during 116th, [] if none known.
- companies_sponsorships: list of stock ticker symbols ONLY (uppercase, max 10) tied to 2020 election cycle corporate contributors. Omit any company lacking a public ticker; do not include names, only tickers. [] if none.

OUTPUT SCHEMA (EXACT KEYS ONLY):
{{
  "sex": "male|female|unknown|null",
  "party": "DEM|REP|IND|OTHER|null",
  "birth_date": "YYYY-MM-DD or null",
  "state": "string or null",
  "city": "string or null",
  "university": "string or null",
  "seniority_in_congress_years": integer or null,
  "committees_116": ["string", ...],
  "companies_sponsorships": ["string", ...]
}}

RULES:
- Return JSON only.
- Do NOT include any name field.
- Deduplicate arrays case-insensitively preserving first capitalization.
- Use null (not empty string) when unknown.
- If conflicting data sources, prefer official congressional biographical / congress.gov.
- Tickers: 1-5 uppercase letters (allow a single dot for class, e.g., BRK.B). Exclude invalid entries.
"""

def generate_profile_prompt(politician_name: str) -> str:
    return PROFILE_PROMPT_TEMPLATE.format(politician_name=politician_name)


class PoliticianProfile(BaseModel):
    full_name: Optional[str]
    sex: Optional[str] = Field(description='"male", "female", or "unknown"')
    party: Optional[str] = Field(description='One of DEM, REP, IND, OTHER')
    birth_date: Optional[str] = Field(description="YYYY-MM-DD or null")
    state: Optional[str]
    city: Optional[str]
    university: Optional[str]
    seniority_in_congress_years: Optional[int]
    committees_116: List[str]
    companies_sponsorships: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "input_name": "John Doe",
                "full_name": "John A. Doe",
                "sex": "male",
                "party": "DEM",
                "birth_date": "1965-04-12",
                "state": "Washington",
                "city": "Seattle",
                "university": "University of Washington",
                "seniority_in_congress_years": 8,
                "committees_116": ["Committee on Energy and Commerce"],
                "companies_sponsorships": ["TSLA", "AAPL"]
            }
        }

__all__ = ["generate_profile_prompt", "PoliticianProfile"]