# Timetable Shared Course Mapping Design

## Goal
Use the Semester 1 timetable workbook and student handbook to make every currently imported question-bank course available to all programmes that actually take that course, then generate a markdown catalog of faculties, programmes, and course offerings.

## Design
- Treat `timetable/Final_Examination_Timetable_Semester_One_2025_2026_Academic_Year.xlsx` as the source of truth for shared course offerings by class prefix and level.
- Map timetable class prefixes such as `CE`, `EL`, and `MN` to existing programme codes in `src/domains/catalog/data.py`.
- Only activate timetable-derived offerings for course slugs that already exist in the imported question bank (`question_bank.course_slug`), so the bots do not show courses with no quizzes yet.
- Normalize obvious timetable title variants and typos, for example `GENERAL PYSCHOLOGY` and `GENERAL PSYCHOLOGY` should both map to `general-psychology`.
- Keep the student handbook PDF as the faculty/programme reference for documentation and for identifying programme names behind timetable prefixes.
- Generate a markdown reference under `docs/` that lists faculties, programmes, and courses by level/semester from the updated catalog seed.

## Validation
- Reseed the catalog and verify shared courses appear under all expected programmes.
- Run the catalog/profile/home tests that cover programme, level, and course selection.
- Query representative shared courses such as `general-psychology`, `differential-equations`, `applied-electricity`, and `linear-algebra`.
