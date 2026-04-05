from collections.abc import Mapping


class HomeService:
    def __init__(self, button_labels: Mapping[str, str] | None = None):
        self.button_labels = dict(button_labels or {})

    def build_home(
        self,
        profile: Mapping[str, str | bool | None] | None,
        *,
        has_active_quiz: bool = False,
        include_performance_button: bool = True,
    ) -> dict:
        safe_profile = profile or {}
        message = self._build_message(safe_profile)
        buttons = self._build_buttons(
            has_active_quiz=has_active_quiz,
            include_performance_button=include_performance_button,
        )
        return {"message": message, "buttons": buttons}

    def _build_message(self, profile: Mapping[str, str | bool | None]) -> str:
        faculty = profile.get("faculty_name") or "Not set"
        program = profile.get("program_name") or "Not set"
        level = profile.get("level_name") or "Not set"
        semester = profile.get("semester_name") or "Not set"

        return (
            "Study Home\n\n"
            f"Faculty: {faculty}\n"
            f"Program: {program}\n"
            f"Level: {level}\n"
            f"Semester: {semester}"
        )

    def _build_buttons(
        self,
        *,
        has_active_quiz: bool,
        include_performance_button: bool,
    ) -> list[list[dict[str, str]]]:
        buttons = [
            [
                {
                    "label": self._label("start_quiz", "Start Quiz"),
                    "callback": "home:start_quiz",
                }
            ],
        ]

        if has_active_quiz:
            buttons.append(
                [
                    {
                        "label": self._label("continue_quiz", "Continue Quiz"),
                        "callback": "home:continue_quiz",
                    }
                ]
            )

        if include_performance_button:
            buttons.append(
                [
                    {
                        "label": self._label("performance", "Performance"),
                        "callback": "home:performance",
                    }
                ]
            )

        buttons.extend(
            [
                [
                    {
                        "label": self._label("study_settings", "Study Settings"),
                        "callback": "home:study_settings",
                    }
                ],
                [
                    {
                        "label": self._label("help", "Help"),
                        "callback": "home:help",
                    }
                ],
            ]
        )
        return buttons

    def _label(self, key: str, fallback: str) -> str:
        return self.button_labels.get(key) or fallback
