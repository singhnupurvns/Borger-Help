"""
The rules engine: pure Python, zero LLM calls, fully unit-testable.

Given a CitizenProfile and a list of SchemeRule objects, for each scheme it
returns an EligibilityResult explaining exactly which individual rules passed
or failed, and which pieces of information are still missing (so the
conversational layer knows what to ask the user next).

This is the "explainable AI" part of the project: you can always show *why*
someone is or isn't eligible, rather than trusting an opaque LLM judgment.
"""

from typing import List

from models import CitizenProfile, EligibilityResult, ResidencyStatus, RuleCheck, SchemeRule


def _check_age(profile: CitizenProfile, rule: SchemeRule) -> RuleCheck:
    if rule.min_age is None and rule.max_age is None:
        return RuleCheck(rule_name="age", passed=True, detail="No age restriction.")
    if profile.age is None:
        return RuleCheck(rule_name="age", passed=False, detail="Age not provided yet.")
    if rule.min_age is not None and profile.age < rule.min_age:
        return RuleCheck(
            rule_name="age", passed=False,
            detail=f"Must be at least {rule.min_age}, you are {profile.age}."
        )
    if rule.max_age is not None and profile.age > rule.max_age:
        return RuleCheck(
            rule_name="age", passed=False,
            detail=f"Must be at most {rule.max_age}, you are {profile.age}."
        )
    return RuleCheck(rule_name="age", passed=True, detail=f"Age {profile.age} is within range.")


def _check_residency(profile: CitizenProfile, rule: SchemeRule) -> RuleCheck:
    if not rule.allowed_residency:
        return RuleCheck(rule_name="residency", passed=True, detail="No residency restriction.")
    if profile.residency_status == ResidencyStatus.unknown:
        return RuleCheck(rule_name="residency", passed=False, detail="Residency status not provided yet.")
    if profile.residency_status in rule.allowed_residency:
        return RuleCheck(
            rule_name="residency", passed=True,
            detail=f"Residency status '{profile.residency_status.value}' qualifies."
        )
    allowed = ", ".join(r.value for r in rule.allowed_residency)
    return RuleCheck(
        rule_name="residency", passed=False,
        detail=f"Residency status '{profile.residency_status.value}' not in allowed set ({allowed})."
    )


def _check_income(profile: CitizenProfile, rule: SchemeRule) -> RuleCheck:
    if rule.max_income_dkk is None:
        return RuleCheck(rule_name="income", passed=True, detail="No income cap for this scheme.")
    if profile.monthly_income_dkk is None:
        return RuleCheck(rule_name="income", passed=False, detail="Monthly income not provided yet.")
    if profile.monthly_income_dkk <= rule.max_income_dkk:
        return RuleCheck(
            rule_name="income", passed=True,
            detail=f"Income {profile.monthly_income_dkk:.0f} DKK/month is within the {rule.max_income_dkk:.0f} cap."
        )
    return RuleCheck(
        rule_name="income", passed=False,
        detail=f"Income {profile.monthly_income_dkk:.0f} DKK/month exceeds the {rule.max_income_dkk:.0f} cap."
    )


def _check_flag(passed_condition: bool, required: bool, label: str, missing: bool) -> RuleCheck:
    if not required:
        return RuleCheck(rule_name=label, passed=True, detail=f"'{label}' not required for this scheme.")
    if missing:
        return RuleCheck(rule_name=label, passed=False, detail=f"Whether you are '{label}' is not known yet.")
    if passed_condition:
        return RuleCheck(rule_name=label, passed=True, detail=f"You meet the '{label}' requirement.")
    return RuleCheck(rule_name=label, passed=False, detail=f"You do not meet the '{label}' requirement.")


def _check_years_in_denmark(profile: CitizenProfile, rule: SchemeRule) -> RuleCheck:
    if rule.min_years_in_denmark is None:
        return RuleCheck(rule_name="years_in_denmark", passed=True, detail="No minimum residence duration required.")
    if profile.years_in_denmark is None:
        return RuleCheck(rule_name="years_in_denmark", passed=False, detail="Years lived in Denmark not provided yet.")
    if profile.years_in_denmark >= rule.min_years_in_denmark:
        return RuleCheck(
            rule_name="years_in_denmark", passed=True,
            detail=f"{profile.years_in_denmark} years meets the {rule.min_years_in_denmark}-year minimum."
        )
    return RuleCheck(
        rule_name="years_in_denmark", passed=False,
        detail=f"{profile.years_in_denmark} years is below the {rule.min_years_in_denmark}-year minimum."
    )


def evaluate_scheme(profile: CitizenProfile, rule: SchemeRule) -> EligibilityResult:
    checks: List[RuleCheck] = [
        _check_age(profile, rule),
        _check_residency(profile, rule),
        _check_income(profile, rule),
        _check_years_in_denmark(profile, rule),
        _check_flag(profile.is_student, rule.requires_student, "is_student", missing=False),
        _check_flag(profile.has_children, rule.requires_children, "has_children", missing=False),
        _check_flag(
            profile.employment_status.value == "unemployed", rule.requires_unemployed,
            "is_unemployed", missing=profile.employment_status.value == "unknown" and rule.requires_unemployed,
        ),
        _check_flag(profile.is_sick_or_injured, rule.requires_sick, "is_sick_or_injured", missing=False),
        _check_flag(
            profile.employment_status.value == "retired", rule.requires_retired,
            "is_retired", missing=profile.employment_status.value == "unknown" and rule.requires_retired,
        ),
    ]

    missing_info = [c.rule_name for c in checks if "not provided yet" in c.detail or "not known yet" in c.detail]
    # Eligible only if every check that isn't blocked by missing info has passed,
    # AND there is no missing info left (we don't claim eligibility on incomplete data).
    hard_fails = [c for c in checks if not c.passed and c.rule_name not in missing_info]
    eligible = len(hard_fails) == 0 and len(missing_info) == 0

    return EligibilityResult(scheme=rule, eligible=eligible, checks=checks, missing_info=missing_info)


def evaluate_all(profile: CitizenProfile, rules: List[SchemeRule]) -> List[EligibilityResult]:
    """Returns results for every scheme, sorted: eligible first, then
    'needs more info', then clearly not eligible."""
    results = [evaluate_scheme(profile, r) for r in rules]

    def sort_key(res: EligibilityResult):
        if res.eligible:
            return 0
        if res.missing_info:
            return 1
        return 2

    return sorted(results, key=sort_key)