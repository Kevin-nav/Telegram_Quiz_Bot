def test_first_semester_catalog_returns_program_courses():
    from src.domains.catalog.navigation_service import CatalogNavigationService

    service = CatalogNavigationService()
    courses = service.get_courses(
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
    )

    assert courses


def test_electrical_engineering_level_200_first_semester_courses_use_canonical_slugs():
    from src.domains.catalog.navigation_service import CatalogNavigationService

    service = CatalogNavigationService()

    courses = service.get_courses(
        faculty_code="engineering",
        program_code="electrical-and-electronics-engineering",
        level_code="200",
        semester_code="first",
    )

    assert courses == [
        {
            "code": "differential-equations",
            "name": "Differential Equations",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "general-psychology",
            "name": "General Psychology",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "linear-electronics",
            "name": "Linear Electronics",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "programming-in-labview",
            "name": "Programming in LabVIEW",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "programming-in-matlab",
            "name": "Programming in MATLAB/Simulink",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "thermodynamics",
            "name": "Thermodynamics",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "transformers-and-dc-machines",
            "name": "Transformers and DC Machines",
            "level_code": "200",
            "semester_code": "first",
        },
        {
            "code": "workshop-technology-and-practice",
            "name": "Workshop Technology and Practice",
            "level_code": "200",
            "semester_code": "first",
        },
    ]


def test_catalog_seed_payload_exports_normalized_entities():
    from src.domains.catalog.data import build_catalog_seed_payload

    payload = build_catalog_seed_payload()

    assert payload["faculties"]
    assert payload["programs"]
    assert payload["levels"]
    assert payload["semesters"]
    assert payload["courses"]
    assert payload["offerings"]
    assert any(course["code"] == "programming-in-matlab" for course in payload["courses"])
