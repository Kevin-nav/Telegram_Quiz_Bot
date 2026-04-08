"""Static academic catalog for the first Telegram UX slice.

The faculty/program hierarchy comes directly from ``docs/academic_structure.md``.
Engineering Level 100 first-semester mappings now use the course slugs that already
have imported question-bank data, and can be expanded as more ``q_and_a`` folders
are added.
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
            {
                "code": "robotics-engineering-and-artificial-intelligence",
                "name": "Robotics Engineering and Artificial Intelligence",
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
            {"code": "spatial-planning", "name": "Spatial Planning"},
            {"code": "geological-engineering", "name": "Geological Engineering"},
            {"code": "general-drilling", "name": "General Drilling"},
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
            {
                "code": "telecommunications-engineering",
                "name": "Telecommunications Engineering",
            },
        ],
    },
]

_DOCUMENTED_COURSE_PROGRAMS = [
    (
        "Communication Skills",
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

_ENGINEERING_100_FIRST_SEMESTER_COURSES = {
    "electrical-and-electronics-engineering": [
        {"code": "applied-electricity", "name": "Applied Electricity"},
        {"code": "basic-french", "name": "Basic French I"},
        {
            "code": "instruments-and-measurements",
            "name": "Instruments and Measurements",
        },
        {"code": "linear-algebra", "name": "Linear Algebra"},
    ],
    "mechanical-engineering": [
        {"code": "applied-electricity", "name": "Applied Electricity"},
        {"code": "basic-french", "name": "Basic French I"},
        {"code": "linear-algebra", "name": "Linear Algebra"},
    ],
}

_TIMETABLE_PREFIX_PROGRAMS = {
    "CE": "computer-science-and-engineering",
    "CH": "chemical-engineering",
    "CY": "cyber-security",
    "EC": "economics-and-industrial-organization",
    "EL": "electrical-and-electronics-engineering",
    "ES": "environmental-and-safety-engineering",
    "GD": "general-drilling",
    "GL": "geological-engineering",
    "GM": "geomatics-engineering",
    "IS": "information-systems-and-technology",
    "LA": "land-administration",
    "LT": "logistics-and-transport-management",
    "MA": "mathematics",
    "MC": "mechanical-engineering",
    "MN": "mining-engineering",
    "MR": "minerals-engineering",
    "NG": "natural-gas",
    "PE": "petroleum-engineering",
    "PG": "petroleum-geoscience-engineering",
    "RB": "robotics-engineering-and-artificial-intelligence",
    "RN": "renewable-energy-engineering",
    "RP": "petroleum-refinery-and-petrochemical-engineering",
    "SD": "statistical-data-science",
    "SP": "spatial-planning",
}

_TIMETABLE_IMPORTED_COURSE_OFFERINGS = [
    (
        "applied-electricity",
        "Applied Electricity",
        "100",
        [
            "CE",
            "CH",
            "CY",
            "EL",
            "ES",
            "GL",
            "GM",
            "IS",
            "MA",
            "MC",
            "MN",
            "MR",
            "NG",
            "PE",
            "PG",
            "RB",
            "RN",
            "RP",
        ],
    ),
    (
        "basic-french",
        "Basic French I",
        "100",
        [
            "CE",
            "CH",
            "CY",
            "EC",
            "EL",
            "ES",
            "GD",
            "GL",
            "GM",
            "IS",
            "LA",
            "LT",
            "MA",
            "MC",
            "MN",
            "MR",
            "NG",
            "PE",
            "PG",
            "RB",
            "RN",
            "RP",
            "SD",
            "SP",
        ],
    ),
    (
        "differential-equations",
        "Differential Equations",
        "200",
        ["CE", "CY", "EL", "IS", "MC", "RN"],
    ),
    (
        "general-psychology",
        "General Psychology",
        "200",
        [
            "CE",
            "CH",
            "CY",
            "EC",
            "EL",
            "ES",
            "GD",
            "GL",
            "GM",
            "IS",
            "LA",
            "LT",
            "MA",
            "MC",
            "MN",
            "MR",
            "NG",
            "PE",
            "PG",
            "RN",
            "RP",
            "SD",
            "SP",
        ],
    ),
    (
        "linear-algebra",
        "Linear Algebra",
        "100",
        [
            "CE",
            "CH",
            "CY",
            "EL",
            "ES",
            "GL",
            "GM",
            "IS",
            "MC",
            "MN",
            "MR",
            "NG",
            "PE",
            "PG",
            "RB",
            "RN",
            "RP",
        ],
    ),
    (
        "programming-in-matlab",
        "Programming in MATLAB/Simulink",
        "200",
        ["EL", "MC"],
    ),
    (
        "thermodynamics",
        "Thermodynamics",
        "200",
        ["EL", "MC", "MN", "RN"],
    ),
]


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
    seen_by_program = defaultdict(set)
    overridden_programs = set(_ENGINEERING_100_FIRST_SEMESTER_COURSES)

    def add_course(program_code: str, course: dict) -> None:
        dedupe_key = (
            course["code"],
            course["level_code"],
            course["semester_code"],
        )
        if dedupe_key in seen_by_program[program_code]:
            return
        seen_by_program[program_code].add(dedupe_key)
        grouped[program_code].append(course)

    for course_name, program_codes in _DOCUMENTED_COURSE_PROGRAMS:
        course = {
            "code": _slugify_course(course_name),
            "name": course_name,
            "level_code": "100",
            "semester_code": "first",
        }
        for program_code in program_codes:
            if program_code in overridden_programs:
                continue
            add_course(program_code, course)

    for program_code, courses in _ENGINEERING_100_FIRST_SEMESTER_COURSES.items():
        for course in courses:
            add_course(
                program_code,
                {
                    **course,
                    "level_code": "100",
                    "semester_code": "first",
                },
            )

    for course_code, course_name, level_code, class_prefixes in (
        _TIMETABLE_IMPORTED_COURSE_OFFERINGS
    ):
        course = {
            "code": course_code,
            "name": course_name,
            "level_code": level_code,
            "semester_code": "first",
        }
        for class_prefix in class_prefixes:
            program_code = _TIMETABLE_PREFIX_PROGRAMS.get(class_prefix)
            if not program_code:
                continue
            add_course(program_code, course)

    for program_code, courses in _SEE_200_FIRST_SEMESTER_COURSES.items():
        for course in courses:
            add_course(
                program_code,
                {
                    **course,
                    "level_code": "200",
                    "semester_code": "first",
                },
            )

    for course in list(grouped.get("electrical-and-electronics-engineering", [])):
        if course.get("level_code") == "100":
            add_course("telecommunications-engineering", course)

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
