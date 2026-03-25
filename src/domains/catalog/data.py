"""Static academic catalog for the first Telegram UX slice.

The faculty/program hierarchy comes directly from ``docs/academic_structure.md``.
The repo does not currently contain a first-semester course list, so the active
``first`` semester course associations temporarily reuse the documented course
mapping already in the repository until first-semester seed data is added.
"""

from collections import defaultdict


LEVELS = [
    {"code": "100", "name": "Level 100"},
    {"code": "200", "name": "Level 200"},
]

SEMESTERS = [
    {"code": "first", "name": "First Semester", "active": True},
]

FACULTIES = [
    {
        "code": "computing-and-mathematical-sciences",
        "name": "Faculty of Computing and Mathematical Sciences",
        "programs": [
            {"code": "cyber-security", "name": "Cyber Security"},
            {"code": "statistical-data-science", "name": "Statistical Data Science"},
            {
                "code": "information-systems-and-technology",
                "name": "Information Systems and Technology",
            },
            {"code": "mathematics", "name": "Mathematics"},
            {
                "code": "computer-science-and-engineering",
                "name": "Computer Science and Engineering",
            },
        ],
    },
    {
        "code": "petroleum",
        "name": "School of Petroleum",
        "programs": [
            {"code": "natural-gas", "name": "Natural Gas"},
            {"code": "chemical-engineering", "name": "Chemical Engineering"},
            {
                "code": "petroleum-geoscience-engineering",
                "name": "Petroleum Geoscience Engineering",
            },
            {
                "code": "petroleum-refinery-and-petrochemical-engineering",
                "name": "Petroleum Refinery and Petrochemical Engineering",
            },
            {"code": "petroleum-engineering", "name": "Petroleum Engineering"},
        ],
    },
    {
        "code": "integrated-and-mathematical-science",
        "name": "Faculty of Integrated and Mathematical Science",
        "programs": [
            {
                "code": "logistics-and-transport-management",
                "name": "Logistics and Transport Management",
            },
            {
                "code": "economics-and-industrial-organization",
                "name": "Economics and Industrial Organization",
            },
        ],
    },
    {
        "code": "minerals-and-minerals-technology",
        "name": "Faculty of Minerals and Minerals Technology",
        "programs": [
            {"code": "minerals-engineering", "name": "Minerals Engineering"},
            {"code": "mining-engineering", "name": "Mining Engineering"},
        ],
    },
    {
        "code": "geosciences-and-environmental-studies",
        "name": "Faculty of Geosciences and Environmental Studies",
        "programs": [
            {
                "code": "environmental-and-safety-engineering",
                "name": "Environmental and Safety Engineering",
            },
            {"code": "geomatics-engineering", "name": "Geomatics Engineering"},
            {"code": "land-administration", "name": "Land Administration"},
            {"code": "geological-engineering", "name": "Geological Engineering"},
        ],
    },
    {
        "code": "engineering",
        "name": "Faculty of Engineering",
        "programs": [
            {"code": "mechanical-engineering", "name": "Mechanical Engineering"},
            {
                "code": "renewable-energy-engineering",
                "name": "Renewable Energy Engineering",
            },
            {
                "code": "electrical-and-electronics-engineering",
                "name": "Electrical and Electronics Engineering",
            },
        ],
    },
]

_DOCUMENTED_COURSE_PROGRAMS = [
    (
        "Academic Writing",
        [
            "cyber-security",
            "information-systems-and-technology",
            "mathematics",
            "computer-science-and-engineering",
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "economics-and-industrial-organization",
            "minerals-engineering",
            "mining-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
            "land-administration",
            "geological-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Calculus",
        [
            "cyber-security",
            "information-systems-and-technology",
            "computer-science-and-engineering",
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "minerals-engineering",
            "mining-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
            "geological-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Strength Of Materials",
        [
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "minerals-engineering",
            "mining-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
            "geological-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Basic French II",
        [
            "statistical-data-science",
            "cyber-security",
            "mathematics",
            "computer-science-and-engineering",
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "economics-and-industrial-organization",
            "minerals-engineering",
            "mining-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
            "land-administration",
            "geological-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Engineering Drawing",
        [
            "computer-science-and-engineering",
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "minerals-engineering",
            "mining-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
            "geological-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Basic Electronics",
        [
            "computer-science-and-engineering",
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    (
        "Applied Electronics",
        [
            "natural-gas",
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "petroleum-engineering",
            "minerals-engineering",
            "environmental-and-safety-engineering",
            "geomatics-engineering",
        ],
    ),
    (
        "Basic Material Science",
        [
            "mechanical-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
    ("Instruments and Measurements", ["electrical-and-electronics-engineering"]),
    (
        "Analytical Chemistry",
        [
            "chemical-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
        ],
    ),
    (
        "Physical Chemistry",
        [
            "chemical-engineering",
            "petroleum-geoscience-engineering",
            "petroleum-refinery-and-petrochemical-engineering",
            "minerals-engineering",
        ],
    ),
    (
        "Physical and Analytical Chemistry",
        [
            "natural-gas",
            "petroleum-geoscience-engineering",
            "petroleum-engineering",
            "mining-engineering",
            "geological-engineering",
        ],
    ),
    (
        "Web Programming",
        [
            "cyber-security",
            "information-systems-and-technology",
            "computer-science-and-engineering",
        ],
    ),
    (
        "Object Oriented Programming",
        [
            "cyber-security",
            "information-systems-and-technology",
            "computer-science-and-engineering",
            "renewable-energy-engineering",
            "electrical-and-electronics-engineering",
        ],
    ),
]

_SEE_200_FIRST_SEMESTER_COURSES = {
    "electrical-and-electronics-engineering": [
        {
            "code": "transformers-and-dc-machines",
            "name": "Transformers and DC Machines",
        },
        {
            "code": "linear-electronics",
            "name": "Linear Electronics",
        },
        {
            "code": "programming-in-labview",
            "name": "Programming in LabVIEW",
        },
        {
            "code": "workshop-technology-and-practice",
            "name": "Workshop Technology and Practice",
        },
        {
            "code": "thermodynamics",
            "name": "Thermodynamics",
        },
        {
            "code": "differential-equations",
            "name": "Differential Equations",
        },
        {
            "code": "programming-in-matlab",
            "name": "Programming in MATLAB/Simulink",
        },
        {
            "code": "general-psychology",
            "name": "General Psychology",
        },
    ]
}


def _slugify_course(course_name: str) -> str:
    return (
        course_name.lower()
        .replace("&", "and")
        .replace("ii", "2")
        .replace("  ", " ")
        .replace(" ", "-")
    )


def _build_program_courses():
    grouped = defaultdict(list)
    for course_name, program_codes in _DOCUMENTED_COURSE_PROGRAMS:
        course = {
            "code": _slugify_course(course_name),
            "name": course_name,
            "level_code": "100",
            "semester_code": "first",
        }
        for program_code in program_codes:
            grouped[program_code].append(course)

    for program_code, courses in _SEE_200_FIRST_SEMESTER_COURSES.items():
        for course in courses:
            grouped[program_code].append(
                {
                    **course,
                    "level_code": "200",
                    "semester_code": "first",
                }
            )

    return {
        program_code: sorted(courses, key=lambda entry: entry["name"])
        for program_code, courses in grouped.items()
    }


PROGRAM_COURSES = _build_program_courses()


def build_catalog_seed_payload() -> dict[str, list[dict]]:
    programs: list[dict] = []
    courses_by_code: dict[str, dict] = {}
    offerings: list[dict] = []

    for faculty in FACULTIES:
        for program in faculty["programs"]:
            programs.append(
                {
                    "faculty_code": faculty["code"],
                    "code": program["code"],
                    "name": program["name"],
                    "is_active": True,
                }
            )

    for program_code, courses in PROGRAM_COURSES.items():
        for course in courses:
            courses_by_code.setdefault(
                course["code"],
                {
                    "code": course["code"],
                    "name": course["name"],
                    "short_name": None,
                    "description": None,
                    "is_active": True,
                },
            )
            offerings.append(
                {
                    "program_code": program_code,
                    "level_code": course["level_code"],
                    "semester_code": course["semester_code"],
                    "course_code": course["code"],
                    "is_active": True,
                }
            )

    return {
        "faculties": [
            {
                "code": faculty["code"],
                "name": faculty["name"],
                "is_active": True,
            }
            for faculty in FACULTIES
        ],
        "programs": programs,
        "levels": [
            {
                "code": level["code"],
                "name": level["name"],
                "is_active": True,
            }
            for level in LEVELS
        ],
        "semesters": [
            {
                "code": semester["code"],
                "name": semester["name"],
                "is_active": semester.get("active", True),
            }
            for semester in SEMESTERS
        ],
        "courses": sorted(courses_by_code.values(), key=lambda item: item["name"]),
        "offerings": sorted(
            offerings,
            key=lambda item: (
                item["program_code"],
                item["level_code"],
                item["semester_code"],
                item["course_code"],
            ),
        ),
    }
