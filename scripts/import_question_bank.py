from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.domains.question_bank.import_service import QuestionBankImportService


DEFAULT_Q_AND_A_ROOT = Path(__file__).resolve().parents[2] / "q_and_a"


def discover_course_json_files(q_and_a_root: Path) -> dict[str, Path]:
    course_files: dict[str, Path] = {}

    for entry in sorted(q_and_a_root.iterdir(), key=lambda item: item.name):
        if not entry.is_dir():
            continue

        json_path = entry / "scored_cleaned.json"
        if json_path.exists():
            course_files[entry.name] = json_path

    return course_files


async def import_courses(
    *,
    service: QuestionBankImportService,
    q_and_a_root: Path,
    course_slug: str | None = None,
    import_all: bool = False,
):
    discovered = discover_course_json_files(q_and_a_root)

    if course_slug:
        json_path = discovered.get(course_slug)
        if json_path is None:
            raise ValueError(
                f"No scored_cleaned.json found for course '{course_slug}' in {q_and_a_root}"
            )
        return [
            await service.import_course_from_json(
                course_id=course_slug,
                course_slug=course_slug,
                json_path=json_path,
            )
        ]

    if not import_all:
        raise ValueError("Choose either a specific course or --all.")

    reports = []
    for discovered_course_slug, json_path in discovered.items():
        reports.append(
            await service.import_course_from_json(
                course_id=discovered_course_slug,
                course_slug=discovered_course_slug,
                json_path=json_path,
            )
        )
    return reports


def format_report_summary(report) -> str:
    return (
        f"{report.course_slug}: total={report.total_rows} "
        f"ready={report.successful_rows} failed={report.failed_rows}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import scored question banks into Postgres.")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--course",
        help="Course slug under q_and_a/, for example linear-electronics.",
    )
    target_group.add_argument(
        "--all",
        action="store_true",
        help="Import all discovered courses with scored_cleaned.json.",
    )
    parser.add_argument(
        "--q-and-a-root",
        type=Path,
        default=DEFAULT_Q_AND_A_ROOT,
        help="Path to the shared q_and_a directory.",
    )
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    service = QuestionBankImportService()
    reports = await import_courses(
        service=service,
        q_and_a_root=args.q_and_a_root,
        course_slug=args.course,
        import_all=args.all,
    )

    for report in reports:
        print(format_report_summary(report))

    total_rows = sum(report.total_rows for report in reports)
    total_ready = sum(report.successful_rows for report in reports)
    total_failed = sum(report.failed_rows for report in reports)
    print(f"overall: total={total_rows} ready={total_ready} failed={total_failed}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
