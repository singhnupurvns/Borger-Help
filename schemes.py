"""
Curated database of Danish welfare schemes, encoded as SchemeRule Pydantic models.

Scope is deliberately limited to 7 well-known schemes (per project brief section 9)
rather than the entire welfare system. Adding an 8th scheme is just adding one
more SchemeRule(...) entry below — no other code changes needed.

NOTE ON ACCURACY: the numeric thresholds here (income caps, age bands, etc.)
are illustrative placeholders based on publicly known general structure of each
scheme, not verified current legal thresholds. Before using this for real
guidance, each value should be checked against the current text on borger.dk,
since these figures change yearly (e.g. with satser-regulering each January).
This is noted again in the Streamlit UI disclaimer.
"""

from typing import List

from models import ResidencyStatus, SchemeRule

SCHEMES: List[SchemeRule] = [
    SchemeRule(
        scheme_id="su",
        display_name="SU (State Education Grant)",
        danish_name="Statens Uddannelsesstøtte",
        description=(
            "Monthly grant for people in Denmark studying at an approved "
            "further/higher education programme, to help cover living costs."
        ),
        min_age=18,
        max_age=None,
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.eu_citizen,
        ],
        requires_student=True,
        official_url="https://www.su.dk/",
        documents_needed=[
            "MitID login",
            "Proof of enrollment at an approved institution",
            "NemKonto (bank account) registered",
        ],
    ),
    SchemeRule(
        scheme_id="boligstoette",
        display_name="Boligstøtte (Housing Support)",
        danish_name="Boligstøtte",
        description=(
            "Monthly subsidy toward rent for low-income households, "
            "based on income, rent level, household size and number of children."
        ),
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.refugee,
            ResidencyStatus.eu_citizen,
        ],
        max_income_dkk=25000,
        official_url="https://www.borger.dk/Bolig-og-flytning/Boligstoette",
        documents_needed=[
            "MitID login",
            "Lease agreement (lejekontrakt)",
            "Household income details",
        ],
    ),
    SchemeRule(
        scheme_id="sygedagpenge",
        display_name="Sygedagpenge (Sick Leave Benefit)",
        danish_name="Sygedagpenge",
        description=(
            "Income replacement paid when you cannot work due to your own "
            "illness or injury, typically after employer-paid sick leave ends."
        ),
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.work_visa,
            ResidencyStatus.eu_citizen,
        ],
        requires_sick=True,
        official_url="https://www.borger.dk/Arbejde-dagpenge-ferie/Sygdom-og-arbejde/Sygedagpenge",
        documents_needed=[
            "MitID login",
            "Doctor's note (lægeerklæring) if requested",
            "Employer's sick-leave notification (if employed)",
        ],
    ),
    SchemeRule(
        scheme_id="dagpenge",
        display_name="Dagpenge (Unemployment Benefit)",
        danish_name="Arbejdsløshedsdagpenge",
        description=(
            "Unemployment benefit for members of an A-kasse (unemployment "
            "insurance fund) who have lost their job and are actively job-seeking."
        ),
        min_age=18,
        max_age=65,
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.eu_citizen,
            ResidencyStatus.work_visa,
        ],
        requires_unemployed=True,
        official_url="https://www.borger.dk/Arbejde-dagpenge-ferie/Dagpenge-ved-ledighed",
        documents_needed=[
            "MitID login",
            "A-kasse membership confirmation",
            "CV registered on Jobnet.dk",
        ],
    ),
    SchemeRule(
        scheme_id="integrationsydelse",
        display_name="Selvforsørgelses- og hjemrejseydelse (Integration Allowance)",
        danish_name="Selvforsørgelses- og hjemrejseydelse / Integrationsydelse",
        description=(
            "Lower-tier public support for newly arrived refugees and certain "
            "immigrants who do not yet qualify for standard cash assistance, "
            "combined with an integration programme through the local municipality."
        ),
        allowed_residency=[ResidencyStatus.refugee],
        official_url="https://www.borger.dk/Familie-og-boern/Flygtninge-og-familiesammenfoerte",
        documents_needed=[
            "MitID / residence permit documentation",
            "Municipality integration contract (integrationskontrakt)",
            "CPR registration",
        ],
    ),
    SchemeRule(
        scheme_id="boernecheck",
        display_name="Børne- og ungeydelse (Child Benefit)",
        danish_name="Børne- og ungeydelse",
        description=(
            "Quarterly tax-free payment to parents/guardians of children "
            "under 18 who are resident in Denmark, means-tested at higher incomes."
        ),
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.refugee,
            ResidencyStatus.eu_citizen,
            ResidencyStatus.work_visa,
        ],
        requires_children=True,
        official_url="https://www.borger.dk/Familie-og-boern/Boernefamilier/boerne-og-ungeydelse",
        documents_needed=[
            "MitID login",
            "Child(ren)'s CPR number(s)",
            "NemKonto registered",
        ],
    ),
    SchemeRule(
        scheme_id="folkepension",
        display_name="Folkepension (State Pension)",
        danish_name="Folkepension",
        description=(
            "Basic state pension for people who have reached Denmark's state "
            "pension age, based on years of residence in Denmark."
        ),
        min_age=67,
        allowed_residency=[
            ResidencyStatus.citizen,
            ResidencyStatus.permanent_resident,
            ResidencyStatus.eu_citizen,
        ],
        min_years_in_denmark=3,
        official_url="https://www.borger.dk/Pension-og-efterloen/Folkepension",
        documents_needed=[
            "MitID login",
            "Proof of years of residence in Denmark",
            "NemKonto registered",
        ],
    ),
]


def get_scheme_by_id(scheme_id: str) -> SchemeRule:
    for s in SCHEMES:
        if s.scheme_id == scheme_id:
            return s
    raise KeyError(f"Unknown scheme_id: {scheme_id}")