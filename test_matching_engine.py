"""
Unit tests for the matching engine — run with: pytest test_matching_engine.py -v

These demonstrate the core viva talking point: eligibility is a pure,
deterministic function of (CitizenProfile, SchemeRule) with zero LLM
involvement, so it can be tested like any normal business logic.
"""

from matching_engine import evaluate_all, evaluate_scheme
from models import CitizenProfile, EmploymentStatus, ResidencyStatus
from schemes import SCHEMES, get_scheme_by_id


def test_student_qualifies_for_su():
    profile = CitizenProfile(
        age=22,
        residency_status=ResidencyStatus.citizen,
        is_student=True,
        employment_status=EmploymentStatus.student,
    )
    result = evaluate_scheme(profile, get_scheme_by_id("su"))
    assert result.eligible is True


def test_underage_does_not_qualify_for_su():
    profile = CitizenProfile(
        age=16,
        residency_status=ResidencyStatus.citizen,
        is_student=True,
    )
    result = evaluate_scheme(profile, get_scheme_by_id("su"))
    assert result.eligible is False


def test_incomplete_profile_is_not_falsely_eligible():
    # No age, no residency status given at all yet.
    profile = CitizenProfile(is_student=True)
    result = evaluate_scheme(profile, get_scheme_by_id("su"))
    assert result.eligible is False
    assert "age" in result.missing_info or "residency" in result.missing_info


def test_refugee_qualifies_for_integration_allowance():
    profile = CitizenProfile(residency_status=ResidencyStatus.refugee)
    result = evaluate_scheme(profile, get_scheme_by_id("integrationsydelse"))
    assert result.eligible is True


def test_high_income_excluded_from_boligstoette():
    profile = CitizenProfile(
        residency_status=ResidencyStatus.citizen,
        monthly_income_dkk=50000,
    )
    result = evaluate_scheme(profile, get_scheme_by_id("boligstoette"))
    assert result.eligible is False
    failed_names = [c.rule_name for c in result.checks if not c.passed]
    assert "income" in failed_names


def test_pensioner_profile_matches_folkepension_and_not_su():
    profile = CitizenProfile(
        age=70,
        residency_status=ResidencyStatus.citizen,
        years_in_denmark=40,
        employment_status=EmploymentStatus.retired,
    )
    results = evaluate_all(profile, SCHEMES)
    eligible_ids = [r.scheme.scheme_id for r in results if r.eligible]
    assert "folkepension" in eligible_ids
    assert "su" not in eligible_ids


def test_evaluate_all_sorts_eligible_first():
    profile = CitizenProfile(
        age=25,
        residency_status=ResidencyStatus.citizen,
        is_student=True,
        employment_status=EmploymentStatus.student,
    )
    results = evaluate_all(profile, SCHEMES)
    eligible_flags = [r.eligible for r in results]
    # Once we hit a False, we should never see a True again after it.
    seen_false = False
    for flag in eligible_flags:
        if not flag:
            seen_false = True
        else:
            assert not seen_false, "Eligible scheme appeared after a non-eligible one" 
            