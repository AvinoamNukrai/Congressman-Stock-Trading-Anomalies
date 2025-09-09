"""Prompt template and factory for transaction conflict-of-interest analysis."""
from pydantic import BaseModel, Field
from typing import List


PROMPT_TEMPLATE = """
You are a senior forensic financial analyst specializing in political conflicts of interest. Your task is to investigate a potential connection between a politician and a company, based on their legislative activities and business interests.

Instructions:

1. Analyze Politician's Legislative Role:
   * Identify and list all subcommittees of the 116th Congress that {politician_name} is a member of.

2. Analyze Company's Business Profile:
   * Determine the primary business sector of {company_name}.
   * Identify relevant industry tags or keywords (e.g., "clean energy," "telecommunications," "pharmaceuticals").

3. Cross-Reference Agendas:
   * Identify the legislative agenda and stated policy priorities of {politician_name}.
   * Assess if there is a direct or indirect relationship between {politician_name}'s agenda and {company_name}'s sector or industry tags.

4. Evaluate Legislative Impact:
   * Using the provided date ({date_of_event}) as a focal point, find and describe any legislative decisions, bills, or votes that took place within a 5-month window (from 2.5 months before to 2.5 months after {date_of_event}) within {politician_name}'s subcommittees.
   * For each decision, determine if it specifically benefited or harmed {company_name}.
   * Note whether {politician_name} publicly supported, led, or opposed these decisions.

5. Synthesize and Conclude:
   * Based on your analysis, please return the data as a JSON object matching the schema below and nothing else.
   * For any 'true' boolean field, provide a brief reference or proof.

Output JSON Schema:
{{
  "type": "object",
  "properties": {{
    "subcommittees": {{"type": "array", "items": {{"type": "string"}}}},
    "supporting_agenda": {{"type": "boolean"}},
    "supporting_agenda_explanation": {{"type": "string"}},
    "direct_legislative_connection": {{"type": "boolean"}},
    "direct_legislative_connection_proof": {{"type": "string"}},
    "subcommittee_decision": {{"type": "boolean"}},
    "subcommittee_decision_proof": {{"type": "string"}}
  }},
  "required": [
    "subcommittees",
    "supporting_agenda",
    "supporting_agenda_explanation",
    "direct_legislative_connection",
    "direct_legislative_connection_proof",
    "subcommittee_decision",
    "subcommittee_decision_proof"
  ]
}}
"""

def generate_prompt(politician_name: str, company_name: str, date_of_event: str) -> str:
    """Return a formatted analysis prompt."""
    return PROMPT_TEMPLATE.format(
        politician_name=politician_name,
        company_name=company_name,
        date_of_event=date_of_event,
    )


class TransactionAnalysis(BaseModel):
    subcommittees: List[str] = Field(description="List of subcommittees the politician is a member of.")
    supporting_agenda: bool = Field(description="Does the politician's agenda support the company's business sector?")
    supporting_agenda_explanation: str = Field(description="Short 1–3 sentence explanation summarizing the politician's agenda and why it does or does not align with the company's sector.")
    direct_legislative_connection: bool = Field(description="Is there a direct legislative connection between the politician's activities and the company?")
    direct_legislative_connection_proof: str = Field(description="Proof or reference for the direct legislative connection, if one exists.")
    subcommittee_decision: bool = Field(description="Was there a relevant subcommittee decision that benefited the company within the specified time window?")
    subcommittee_decision_proof: str = Field(description="Proof or reference for the subcommittee decision, if one exists.")

    class Config:
        json_schema_extra = {
            "example": {
                "subcommittees": [
                    "Subcommittee on Antitrust, Commercial and Administrative Law",
                    "Subcommittee on Crime, Terrorism, and Homeland Security"
                ],
                "supporting_agenda": True,
                "supporting_agenda_explanation": "The member advocates antitrust modernization and digital market oversight, which aligns with the competitive positioning of large platform companies in the member's portfolio.",
                "direct_legislative_connection": True,
                "direct_legislative_connection_proof": "See remarks in March 2020 Judiciary hearing on market dominance (Congressional Record).",
                "subcommittee_decision": True,
                "subcommittee_decision_proof": "See markup session transcript (March 10, 2020) referencing preliminary antitrust inquiry scope."
            }
        }
