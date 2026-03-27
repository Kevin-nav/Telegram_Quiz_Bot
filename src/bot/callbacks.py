def build_callback(*parts: str) -> str:
    return ":".join(parts)


def parse_callback(callback_data: str) -> list[str]:
    return callback_data.split(":")


def home_callback(action: str) -> str:
    return build_callback("home", action)


def profile_callback(section: str, value: str) -> str:
    return build_callback("profile", section, value)


def profile_faculty_callback(faculty_code: str) -> str:
    return profile_callback("faculty", faculty_code)


def profile_program_callback(program_code: str) -> str:
    return profile_callback("program", program_code)


def profile_level_callback(level_code: str) -> str:
    return profile_callback("level", level_code)


def profile_semester_callback(semester_code: str) -> str:
    return profile_callback("semester", semester_code)


def profile_course_callback(course_code: str) -> str:
    return profile_callback("course", course_code)


def profile_back_callback() -> str:
    return build_callback("profile", "back")


def profile_cancel_callback() -> str:
    return build_callback("profile", "cancel")


def quiz_length_callback(length: int) -> str:
    return build_callback("quiz", "length", str(length))


def quiz_course_callback(course_code: str) -> str:
    return build_callback("quiz", "course", course_code)


def report_start_callback(scope: str) -> str:
    return build_callback("report", "start", scope)


def report_reason_callback(scope: str, reason: str) -> str:
    return build_callback("report", "reason", scope, reason)


def report_skip_note_callback(scope: str) -> str:
    return build_callback("report", "skip_note", scope)


def report_cancel_callback(scope: str) -> str:
    return build_callback("report", "cancel", scope)
