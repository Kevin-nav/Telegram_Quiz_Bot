import re
import os
import subprocess
import tempfile
from pathlib import Path

from pdf2image import convert_from_path


def escape_latex_text(text: str) -> str:
    """Escape LaTeX special characters in non-math portions of text.

    Splits the string on ``$…$`` math spans (inline math), escapes the
    text portions, and leaves the math spans untouched.  The characters
    escaped are those that would otherwise confuse pdflatex when they appear
    outside math mode: ``_ ^ # & % { }``.
    """
    # Split on inline math: $...$ (non-greedy, doesn't cross newlines within $)
    # We capture the delimiter so we can re-assemble correctly.
    parts = re.split(r'(\$[^$\\]*(?:\\.[^$\\]*)*\$)', text)
    escaped_parts = []
    for i, part in enumerate(parts):
        if part.startswith('$') and part.endswith('$') and len(part) > 1:
            # Math span — leave untouched
            escaped_parts.append(part)
        else:
            # Text span — escape special chars
            # Order matters: \ must go first if you ever add it
            part = part.replace('_', r'\_')
            part = part.replace('^', r'\^{}')
            part = part.replace('#', r'\#')
            part = part.replace('&', r'\&')
            part = part.replace('%', r'\%')
            escaped_parts.append(part)
    return ''.join(escaped_parts)


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

VARIANT_ORDERS = (
    (0, 1, 2, 3),
    (1, 0, 3, 2),
    (2, 3, 0, 1),
    (3, 2, 1, 0),
)


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
            )
            if result.returncode != 0:
                return False

            pdf_file = Path(temp_dir) / "render.pdf"
            if not pdf_file.exists():
                return False

            images = convert_from_path(str(pdf_file), dpi=300, first_page=1, last_page=1)
            if not images:
                return False

            images[0].save(output_path, "PNG")
            return True
        except Exception:
            return False


def build_latex_option_variants(options: list[str]) -> list[list[str]]:
    if len(options) != 4:
        raise ValueError("LaTeX option variants currently require exactly four options.")

    return [[options[index] for index in order] for order in VARIANT_ORDERS]


def build_variant_order_maps(option_count: int) -> list[list[int]]:
    if option_count != 4:
        raise ValueError("LaTeX variant order maps currently require exactly four options.")
    return [list(order) for order in VARIANT_ORDERS]


def _build_option_box(label: str, option_text: str) -> str:
    return (
        r"\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, "
        r"boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white]"
        "\n"
        rf"\textbf{{\textcolor{{mainYellow!90!black}}{{{label}}}}}\hspace{{0.3cm}} {escape_latex_text(option_text)}"
        "\n"
        r"\end{tcolorbox}"
    )


def build_question_latex(question_text: str, options: list[str]) -> str:
    option_boxes = [
        _build_option_box(chr(65 + index), option_text)
        for index, option_text in enumerate(options)
    ]
    return QUESTION_TEMPLATE.replace("{QUESTION_TEXT}", escape_latex_text(question_text)).replace(
        "{OPTIONS}", "\n".join(option_boxes)
    )


def build_explanation_latex(correct_option_text: str, explanation_text: str) -> str:
    return (
        EXPLANATION_TEMPLATE.replace("{CORRECT_OPTION_TEXT}", escape_latex_text(correct_option_text))
        .replace("{EXPLANATION_TEXT}", escape_latex_text(explanation_text))
    )
