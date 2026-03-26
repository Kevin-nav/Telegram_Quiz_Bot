from src.domains.catalog.service import CatalogService


class CatalogNavigationService:
    def __init__(self, catalog_service: CatalogService | None = None):
        self.catalog_service = catalog_service

    async def get_faculties(self) -> list[dict]:
        return await self._catalog_service().get_faculties()

    async def get_programs(self, faculty_code: str) -> list[dict]:
        return await self._catalog_service().get_programs(faculty_code)

    async def get_levels(self, program_code: str) -> list[dict]:
        return await self._catalog_service().get_levels(program_code)

    async def get_semesters(self, program_code: str, level_code: str) -> list[dict]:
        return await self._catalog_service().get_semesters(program_code, level_code)

    async def get_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict]:
        return await self._catalog_service().get_courses(
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )

    def _catalog_service(self) -> CatalogService:
        return self.catalog_service or CatalogService()
