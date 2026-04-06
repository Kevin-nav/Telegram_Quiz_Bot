from __future__ import annotations

from dataclasses import dataclass, field


TANJAH_BOT_ID = "tanjah"
ADARKWA_BOT_ID = "adarkwa"
BOT_CONFIG_KEY = "bot_config"


@dataclass(frozen=True, slots=True)
class BotThemeConfig:
    brand_name: str
    image_header_text: str
    image_footer_hashtag: str
    image_footer_username: str
    image_watermark_text: str
    primary_color_hex: str
    accent_color_hex: str
    welcome_message_template: str = ""
    welcome_image_path: str | None = None
    button_labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BotRuntimeConfig:
    bot_id: str
    telegram_bot_token: str | None
    webhook_secret: str | None
    webhook_path: str
    allowed_course_codes: tuple[str, ...]
    theme: BotThemeConfig
    profile_setup_start_step: str = "faculty"
    fixed_faculty_code: str | None = None
    fixed_faculty_name: str | None = None
    fixed_level_code: str | None = None
    fixed_level_name: str | None = None

    def course_is_allowed(self, course_code: str | None) -> bool:
        if not self.allowed_course_codes or not course_code:
            return True
        return course_code in self.allowed_course_codes


DEFAULT_BOT_THEMES = {
    TANJAH_BOT_ID: BotThemeConfig(
        brand_name="Tanjah",
        image_header_text="TANJAH PHILP",
        image_footer_hashtag="#YOUR_FINANCIAL_ENGINEER",
        image_footer_username="@study_with_tanjah_bot",
        image_watermark_text="TANJAH",
        primary_color_hex="1A6B3A",
        accent_color_hex="F5B800",
        welcome_message_template=(
            "🚀 Welcome to {brand_name}'s Study Bot, {learner_name}!\n\n"
            "Let's get you ready for your exams. Set up your study profile first, "
            "then you can access all the quizzes directly from the home screen."
        ),
        welcome_image_path=None,
        button_labels={
            "start_quiz": "Start Quiz",
            "continue_quiz": "Continue Quiz",
            "study_settings": "Study Profile",
            "performance": "Performance",
            "help": "Help",
        },
    ),
    ADARKWA_BOT_ID: BotThemeConfig(
        brand_name="Adarkwa",
        image_header_text="ADARKWA",
        image_footer_hashtag="#ADARKWA_STUDY",
        image_footer_username="@Adarkwa_Study_Bot",
        image_watermark_text="ADARKWA",
        primary_color_hex="123B7A",
        accent_color_hex="F59E0B",
        welcome_message_template=(
            "👋 Welcome to {brand_name}'s Study Bot, {learner_name}!\n\n"
            "The future isn't just coming; we are owning it! 🛠️⚙️ Brought to you by Team Adarkwah "
            "and The View Projector, this tool is here to empower you to take charge of your academics.\n\n"
            "Set up your study profile once, then use the home screen to jump straight into practice quizzes. "
            "Let's keep Owning The Future! #OTF"
        ),
        welcome_image_path="assets/Adarkwa.jpg",
        button_labels={
            "start_quiz": "Start Practice",
            "continue_quiz": "Resume Practice",
            "study_settings": "Study Setup",
            "performance": "Progress",
            "help": "Help",
        },
    ),
}

DEFAULT_PROFILE_SETUP_OVERRIDES = {
    TANJAH_BOT_ID: {
        "profile_setup_start_step": "faculty",
        "fixed_faculty_code": None,
        "fixed_faculty_name": None,
        "fixed_level_code": None,
        "fixed_level_name": None,
    },
    ADARKWA_BOT_ID: {
        "profile_setup_start_step": "program",
        "fixed_faculty_code": "engineering",
        "fixed_faculty_name": "Faculty Of Engineering",
        "fixed_level_code": "100",
        "fixed_level_name": "Level 100",
    },
}


def parse_allowed_course_codes(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return ()
    return tuple(
        course_code.strip()
        for course_code in raw_value.split(",")
        if course_code.strip()
    )


def normalize_webhook_path(path: str | None, *, fallback_bot_id: str) -> str:
    normalized_path = (path or f"/webhook/{fallback_bot_id}").strip()
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    return normalized_path


def get_bot_config(bot_data: dict, default_bot_id: str = TANJAH_BOT_ID) -> BotRuntimeConfig:
    bot_config = bot_data.get(BOT_CONFIG_KEY)
    if isinstance(bot_config, BotRuntimeConfig):
        return bot_config

    return BotRuntimeConfig(
        bot_id=default_bot_id,
        telegram_bot_token=None,
        webhook_secret=None,
        webhook_path=normalize_webhook_path(None, fallback_bot_id=default_bot_id),
        allowed_course_codes=(),
        theme=DEFAULT_BOT_THEMES[default_bot_id],
        **DEFAULT_PROFILE_SETUP_OVERRIDES[default_bot_id],
    )
