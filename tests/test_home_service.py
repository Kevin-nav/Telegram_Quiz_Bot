from src.domains.home.service import HomeService


def test_home_service_includes_continue_when_active_quiz_exists():
    service = HomeService()

    home = service.build_home(
        {
            "faculty_name": "Faculty of Engineering",
            "program_name": "Mechanical Engineering",
            "level_name": "Level 100",
            "semester_name": "First Semester",
            "course_name": "Calculus",
        },
        has_active_quiz=True,
    )

    flattened_callbacks = [
        button["callback"] for row in home["buttons"] for button in row
    ]

    assert "home:continue_quiz" in flattened_callbacks
    assert "Faculty of Engineering" in home["message"]


def test_home_service_hides_continue_when_no_active_quiz_exists():
    service = HomeService()

    home = service.build_home({}, has_active_quiz=False)

    flattened_callbacks = [
        button["callback"] for row in home["buttons"] for button in row
    ]

    assert "home:continue_quiz" not in flattened_callbacks
