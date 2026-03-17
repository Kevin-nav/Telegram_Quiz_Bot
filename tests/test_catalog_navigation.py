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
