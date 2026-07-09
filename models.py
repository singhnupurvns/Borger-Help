"""
Pydantic models for Borger Hjælp.

Two schemas matter most here:
- CitizenProfile: the structured, validated representation of the user's situation
- SchemeRule: the structured, validated representation of one welfare scheme's eligibility rules

The LLM only ever fills in a CitizenProfile. It never decides eligibility.
Eligibility is decided purely by comparing a CitizenProfile against SchemeRule objects
in matching_engine.py — that part contains zero LLM calls, so it's fully testable
and explainable.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ResidencyStatus(str, Enum):
    citizen = "citizen"
    permanent_resident = "permanent_resident"
    refugee = "refugee"
    student_visa = "student_visa"
    work_visa = "work_visa"
    eu_citizen = "eu_citizen"
    unknown = "unknown"


class EmploymentStatus(str, Enum):
    employed = "employed"
    unemployed = "unemployed"
    sick_leave = "sick_leave"
    retired = "retired"
    student = "student"
    unknown = "unknown"


class CitizenProfile(BaseModel):
    """What we know about the user so far. Everything is optional because
    we build this up incrementally across a conversation — the user rarely
    gives every field in one message."""

    age: Optional[int] = Field(default=None, ge=0, le=120)
    residency_status: ResidencyStatus = ResidencyStatus.unknown
    municipality: Optional[str] = None
    monthly_income_dkk: Optional[float] = Field(default=None, ge=0)
    is_student: bool = False
    has_children: bool = False
    number_of_children: int = 0
    employment_status: EmploymentStatus = EmploymentStatus.unknown
    years_in_denmark: Optional[float] = Field(default=None, ge=0)
    is_sick_or_injured: bool = False

    @field_validator("municipality")
    @classmethod
    def _title_case_municipality(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().title() if v else v

    def known_fields(self) -> List[str]:
        """Which fields we actually have real information on (not defaults/unknowns)."""
        known = []
        if self.age is not None:
            known.append("age")
        if self.residency_status != ResidencyStatus.unknown:
            known.append("residency_status")
        if self.municipality:
            known.append("municipality")
        if self.monthly_income_dkk is not None:
            known.append("monthly_income_dkk")
        if self.is_student:
            known.append("is_student")
        if self.has_children:
            known.append("has_children")
        if self.employment_status != EmploymentStatus.unknown:
            known.append("employment_status")
        if self.years_in_denmark is not None:
            known.append("years_in_denmark")
        if self.is_sick_or_injured:
            known.append("is_sick_or_injured")
        return known


class SchemeRule(BaseModel):
    """One Danish welfare scheme, encoded as structured, type-safe eligibility rules."""

    scheme_id: str
    display_name: str
    danish_name: str
    description: str

    min_age: Optional[int] = None
    max_age: Optional[int] = None
    allowed_residency: List[ResidencyStatus] = Field(default_factory=list)
    max_income_dkk: Optional[float] = None
    requires_student: bool = False
    requires_children: bool = False
    requires_unemployed: bool = False
    requires_sick: bool = False
    requires_retired: bool = False
    min_years_in_denmark: Optional[float] = None

    official_url: str
    documents_needed: List[str] = Field(default_factory=list)


class RuleCheck(BaseModel):
    rule_name: str
    passed: bool
    detail: str


class EligibilityResult(BaseModel):
    scheme: SchemeRule
    eligible: bool
    checks: List[RuleCheck]
    missing_info: List[str] = Field(default_factory=list)