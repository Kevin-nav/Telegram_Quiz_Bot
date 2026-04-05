import re
import os
import subprocess
import tempfile
from pathlib import Path

from pdf2image import convert_from_path

from src.bot.runtime_config import BotThemeConfig


def escape_latex_text(text: str) -> str:
    """Escape LaTeX special characters in non-math portions of text.

    Splits the string on ``$…$`` math spans (inline math), escapes the
    text portions, and leaves the math spans untouched.  The characters
    escaped are those that would otherwise confuse pdflatex when they appear
    outside math mode: ``_ ^ # & % { }``.
    """
    # Split on inline math: $...$ (non-greedy, doesn't cross newlines within $)
    # We capture the delimiter so we can re-assemble correctly.
    parts = _split_latex_text_parts(text)
    escaped_parts = []
    for i, part in enumerate(parts):
        if part.startswith('$') and part.endswith('$') and len(part) > 1:
            # Math span — leave untouched
            escaped_parts.append(_normalize_latex_math_span(part))
        else:
            # Text span — escape special chars
            # Order matters: \ must go first if you ever add it
            for unicode_char, latex_replacement in UNICODE_LATEX_REPLACEMENTS.items():
                part = part.replace(unicode_char, latex_replacement)
            part = part.replace('$', r'\$')
            part = part.replace('_', r'\_')
            part = part.replace('^', r'\^{}')
            part = part.replace('#', r'\#')
            part = part.replace('&', r'\&')
            part = part.replace('%', r'\%')
            escaped_parts.append(part)
    return ''.join(escaped_parts)


def _split_latex_text_parts(text: str) -> list[str]:
    parts: list[str] = []
    plain_text: list[str] = []
    index = 0

    while index < len(text):
        character = text[index]
        if character != "$":
            plain_text.append(character)
            index += 1
            continue

        next_character = text[index + 1] if index + 1 < len(text) else ""
        closing_index = text.find("$", index + 1)
        math_body = text[index + 1 : closing_index] if closing_index != -1 else ""

        if (
            next_character.isspace()
            or closing_index == -1
            or not _looks_like_math_span(next_character, math_body)
        ):
            plain_text.append(character)
            index += 1
            continue

        if plain_text:
            parts.append("".join(plain_text))
            plain_text = []

        parts.append(text[index : closing_index + 1])
        index = closing_index + 1

    if plain_text:
        parts.append("".join(plain_text))

    return parts


def _looks_like_math_span(next_character: str, math_body: str) -> bool:
    if not math_body or math_body[-1].isspace():
        return False
    if not next_character.isdigit():
        return True
    return any(
        marker in math_body
        for marker in ("\\", "_", "^", "{", "}", "+", "-", "=", "<", ">", "|", "(", ")")
    )


def _normalize_latex_math_span(part: str) -> str:
    return re.sub(r"\\(?=\d)", r"\\\\", part)


UNICODE_LATEX_REPLACEMENTS = {
    "ε": r"\ensuremath{\epsilon}",
    "μ": r"\ensuremath{\mu}",
    "π": r"\ensuremath{\pi}",
    "Φ": r"\ensuremath{\Phi}",
    "≈": r"\ensuremath{\approx}",
}


QUESTION_TEMPLATE = r"""\documentclass[16pt, border=25pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{tikz}

\definecolor{mainGreen}{HTML}{1A6B3A}
\definecolor{mainYellow}{HTML}{F5B800}

\begin{document}
\begin{tikzpicture}
\node[inner sep=0pt] (content) {
    \begin{minipage}{16cm}
    {\footnotesize\bfseries\textcolor{mainGreen}{TANJAH PHILP}}\par\vspace{0.4cm}
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainGreen!30!white,
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainGreen,
        fonttitle=\large\bfseries, title=\strut Question, coltitle=mainGreen,
        colbacktitle=mainGreen!8!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainGreen!8!white, colback=mainGreen!8!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    {QUESTION_TEXT}
    \end{tcolorbox}
    \vspace{0.4cm}
    \begin{tcbraster}[raster columns=2, raster equal height, raster column skip=0.6cm, raster row skip=0.4cm]
    {OPTIONS}
    \end{tcbraster}
    \vspace{0.8cm}
    \begin{minipage}{\linewidth}
        \textcolor{mainGreen!80!black}{%
            \bfseries\footnotesize \#YOUR\_FINANCIAL\_ENGINEER \hfill \ttfamily\bfseries @study\_with\_tanjah\_bot%
        }
    \end{minipage}
    \end{minipage}
};
\node[overlay, rotate=45, scale=4.5, opacity=0.06, color=mainGreen] at (content.center) {\fontfamily{pzc}\selectfont\Huge TANJAH};
\end{tikzpicture}
\end{document}"""

EXPLANATION_TEMPLATE = r"""\documentclass[16pt, border=25pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{tikz}

\definecolor{mainGreen}{HTML}{1A6B3A}
\definecolor{mainYellow}{HTML}{F5B800}

\begin{document}
\begin{tikzpicture}
\node[inner sep=0pt] (content) {
    \begin{minipage}{16cm}
    {\footnotesize\bfseries\textcolor{mainGreen}{TANJAH PHILP}}\par\vspace{0.4cm}
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow!40!white,
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainYellow,
        fonttitle=\large\bfseries, title=\strut Correct Answer, coltitle=mainYellow!80!black,
        colbacktitle=mainYellow!15!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainYellow!15!white, colback=mainYellow!15!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    {CORRECT_OPTION_TEXT}
    \end{tcolorbox}
    \vspace{0.6cm}
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainGreen!30!white,
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainGreen,
        fonttitle=\large\bfseries, title=\strut Explanation, coltitle=mainGreen,
        colbacktitle=mainGreen!8!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainGreen!8!white, colback=mainGreen!8!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    {EXPLANATION_TEXT}
    \end{tcolorbox}
    \vspace{0.8cm}
    \begin{minipage}{\linewidth}
        \textcolor{mainGreen!80!black}{%
            \bfseries\footnotesize \#YOUR\_FINANCIAL\_ENGINEER \hfill \ttfamily\bfseries @study\_with\_tanjah\_bot%
        }
    \end{minipage}
    \end{minipage}
};
\node[overlay, rotate=45, scale=4.5, opacity=0.06, color=mainGreen] at (content.center) {\fontfamily{pzc}\selectfont\Huge TANJAH};
\end{tikzpicture}
\end{document}"""

THEMED_QUESTION_TEMPLATE = r"""\documentclass[16pt, border=10pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{enumitem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{varwidth}\usepackage{tikz}

\definecolor{questionbg}{rgb}{0.95, 0.95, 0.98}
\definecolor{brandFrame}{HTML}{{BRAND_COLOR}}
\definecolor{brandAccent}{HTML}{{ACCENT_COLOR}}

\begin{document}
\begin{tikzpicture}
\node[inner sep=0pt] (content) {
    \begin{varwidth}{0.9\textwidth}
    {\footnotesize\bfseries\textcolor{brandFrame}{{BRAND_HEADER}}}\par\vspace{0.2cm}
    \begin{tcolorbox}[colback=questionbg, colframe=brandFrame, title=Question]
    {QUESTION_TEXT}
    \end{tcolorbox}
    \vspace{0.3cm}
    \textbf{\textcolor{brandAccent}{Options:}}
    \begin{enumerate}[label=\textbf{\Alph*})]
    {OPTIONS}
    \end{enumerate}
    \vspace{0.2cm}
    {\footnotesize\bfseries\textcolor{brandFrame}{{BRAND_FOOTER_HASHTAG} \hfill \ttfamily {BRAND_FOOTER_USERNAME}}}
    \end{varwidth}
};
\node[overlay, rotate=45, scale=5, opacity=0.08, color=brandFrame] at (content.center) {\textbf{{BRAND_WATERMARK}}};
\end{tikzpicture}
\end{document}"""

THEMED_EXPLANATION_TEMPLATE = r"""\documentclass[16pt, border=10pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{varwidth}\usepackage{tikz}

\definecolor{questionbg}{rgb}{0.95, 0.95, 0.98}
\definecolor{brandFrame}{HTML}{{BRAND_COLOR}}
\definecolor{brandAccent}{HTML}{{ACCENT_COLOR}}

\begin{document}
\begin{tikzpicture}
\node[inner sep=0pt] (content) {
    \begin{varwidth}{0.9\textwidth}
    {\footnotesize\bfseries\textcolor{brandFrame}{{BRAND_HEADER}}}\par\vspace{0.2cm}
    \begin{tcolorbox}[colback=white, colframe=brandAccent, title=Correct Answer]
    {CORRECT_OPTION_TEXT}
    \end{tcolorbox}
    \vspace{0.3cm}
    \begin{tcolorbox}[colback=questionbg, colframe=brandFrame, title=Explanation]
    {EXPLANATION_TEXT}
    \end{tcolorbox}
    \vspace{0.2cm}
    {\footnotesize\bfseries\textcolor{brandFrame}{{BRAND_FOOTER_HASHTAG} \hfill \ttfamily {BRAND_FOOTER_USERNAME}}}
    \end{varwidth}
};
\node[overlay, rotate=45, scale=5, opacity=0.08, color=brandFrame] at (content.center) {\textbf{{BRAND_WATERMARK}}};
\end{tikzpicture}
\end{document}"""

VARIANT_ORDERS = (
    (0, 1, 2, 3),
    (1, 0, 3, 2),
    (2, 3, 0, 1),
    (3, 2, 1, 0),
)


def _build_rotation_orders(option_count: int) -> list[list[int]]:
    if option_count <= 0:
        raise ValueError("LaTeX option variants require at least one option.")
    return [
        [((start_index + offset) % option_count) for offset in range(option_count)]
        for start_index in range(option_count)
    ]


def ensure_miktex_on_path() -> None:
    miktex_path = r"C:\Users\Kevin\AppData\Local\Programs\MiKTeX\miktex\bin\x64"
    if miktex_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = miktex_path + os.pathsep + os.environ.get("PATH", "")


def render_latex_to_png(latex_content: str, output_path: str) -> bool:
    ensure_miktex_on_path()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        tex_file = Path(temp_dir) / "render.tex"
        tex_file.write_text(latex_content, encoding="utf-8")

        try:
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    temp_dir,
                    str(tex_file),
                ],
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=60,
            )
            if result.returncode != 0:
                return False

            pdf_file = Path(temp_dir) / "render.pdf"
            if not pdf_file.exists():
                return False

            images = convert_from_path(
                str(pdf_file),
                dpi=300,
                first_page=1,
                last_page=1,
                timeout=60,
            )
            if not images:
                return False

            images[0].save(output_path, "PNG")
            return True
        except Exception:
            return False


def build_latex_option_variants(options: list[str]) -> list[list[str]]:
    option_orders = build_variant_order_maps(len(options))
    return [[options[index] for index in order] for order in option_orders]



def build_variant_order_maps(option_count: int) -> list[list[int]]:
    if option_count == 4:
        return [list(order) for order in VARIANT_ORDERS]
    return _build_rotation_orders(option_count)


def _build_option_box(label: str, option_text: str) -> str:
    return (
        r"\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, "
        r"boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white]"
        "\n"
        rf"\textbf{{\textcolor{{mainYellow!90!black}}{{{label}}}}}\hspace{{0.3cm}} {escape_latex_text(option_text)}"
        "\n"
        r"\end{tcolorbox}"
    )


def _apply_bot_theme(template: str, bot_theme: BotThemeConfig) -> str:
    return (
        template.replace("{BRAND_COLOR}", bot_theme.primary_color_hex)
        .replace("{ACCENT_COLOR}", bot_theme.accent_color_hex)
        .replace("{BRAND_HEADER}", escape_latex_text(bot_theme.image_header_text))
        .replace(
            "{BRAND_FOOTER_HASHTAG}",
            escape_latex_text(bot_theme.image_footer_hashtag),
        )
        .replace(
            "{BRAND_FOOTER_USERNAME}",
            escape_latex_text(bot_theme.image_footer_username),
        )
        .replace(
            "{BRAND_WATERMARK}",
            escape_latex_text(bot_theme.image_watermark_text),
        )
    )


def build_question_latex(
    question_text: str,
    options: list[str],
    bot_theme: BotThemeConfig | None = None,
) -> str:
    if bot_theme is not None:
        option_items = [
            rf"\item {escape_latex_text(option_text)}"
            for option_text in options
        ]
        return (
            _apply_bot_theme(THEMED_QUESTION_TEMPLATE, bot_theme)
            .replace("{QUESTION_TEXT}", escape_latex_text(question_text))
            .replace("{OPTIONS}", "\n".join(option_items))
        )

    option_boxes = [
        _build_option_box(chr(65 + index), option_text)
        for index, option_text in enumerate(options)
    ]
    return QUESTION_TEMPLATE.replace("{QUESTION_TEXT}", escape_latex_text(question_text)).replace(
        "{OPTIONS}", "\n".join(option_boxes)
    )


def build_explanation_latex(
    correct_option_text: str,
    explanation_text: str,
    bot_theme: BotThemeConfig | None = None,
) -> str:
    if bot_theme is not None:
        return (
            _apply_bot_theme(THEMED_EXPLANATION_TEMPLATE, bot_theme)
            .replace(
                "{CORRECT_OPTION_TEXT}",
                escape_latex_text(correct_option_text),
            )
            .replace(
                "{EXPLANATION_TEXT}",
                escape_latex_text(explanation_text),
            )
        )

    return (
        EXPLANATION_TEMPLATE.replace("{CORRECT_OPTION_TEXT}", escape_latex_text(correct_option_text))
        .replace("{EXPLANATION_TEXT}", escape_latex_text(explanation_text))
    )
