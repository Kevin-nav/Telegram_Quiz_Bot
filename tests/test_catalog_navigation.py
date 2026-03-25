import pytest


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


@pytest.mark.asyncio
async def test_catalog_service_caches_faculties_and_normalizes_repository_records():
    from types import SimpleNamespace

    from src.domains.catalog.service import CatalogService
    from src.infra.redis.state_store import InteractiveStateStore
    from tests.fakes import FakeRedis

    class FakeRepository:
        def __init__(self):
            self.faculty_calls = 0

        async def get_faculty(self, faculty_code: str):
            if faculty_code != "engineering":
                return None
            return SimpleNamespace(code="engineering", name="Faculty of Engineering")

        async def list_faculties(self):
            self.faculty_calls += 1
            return [SimpleNamespace(code="engineering", name="Faculty of Engineering")]

        async def get_program(self, program_code: str):
            if program_code != "electrical-and-electronics-engineering":
                return None
            return SimpleNamespace(
                code="electrical-and-electronics-engineering",
                name="Electrical and Electronics Engineering",
            )

        async def list_programs(self, faculty_code: str | None = None):
            if faculty_code != "engineering":
                return []
            return [
                SimpleNamespace(
                    code="electrical-and-electronics-engineering",
                    name="Electrical and Electronics Engineering",
                )
            ]

        async def list_levels(self):
            return [SimpleNamespace(code="200", name="Level 200")]

        async def list_semesters(self):
            return [SimpleNamespace(code="first", name="First Semester", is_active=True)]

        async def list_courses(self, **kwargs):
            return [
                SimpleNamespace(
                    code="programming-in-matlab",
                    name="Programming in MATLAB/Simulink",
                )
            ]

    service = CatalogService(
        repository=FakeRepository(),
        state_store=InteractiveStateStore(FakeRedis()),
    )

    faculties = await service.get_faculties()
    cached_faculties = await service.get_faculties()
    courses = await service.get_courses(
        "engineering",
        "electrical-and-electronics-engineering",
        "200",
        "first",
    )

    assert faculties == [{"code": "engineering", "name": "Faculty of Engineering"}]
    assert cached_faculties == faculties
    assert courses == [
        {
            "code": "programming-in-matlab",
            "name": "Programming in MATLAB/Simulink",
            "level_code": "200",
            "semester_code": "first",
        }
    ]
