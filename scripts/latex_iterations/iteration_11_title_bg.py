import os
import subprocess
import tempfile
from pathlib import Path
from pdf2image import convert_from_path


def render_latex_to_png(latex_content: str, output_path: str):
    """
    Renders a LaTeX string to a PDF using pdflatex,
    then converts it to a PNG image.
    """
    miktex_path = r"C:\Users\Kevin\AppData\Local\Programs\MiKTeX\miktex\bin\x64"
    if miktex_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = miktex_path + os.pathsep + os.environ.get("PATH", "")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        tex_file = Path(temp_dir) / "render.tex"
        tex_file.write_text(latex_content, encoding="utf-8")

        print("Running pdflatex...")
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
                print("LaTeX rendering failed. Check the log:")
                log_path = Path(temp_dir) / "render.log"
                if log_path.exists():
                    print(log_path.read_text(encoding="utf-8")[:2000])
                else:
                    print(result.stdout)
                    print(result.stderr)
                return False

            pdf_file = Path(temp_dir) / "render.pdf"
            if pdf_file.exists():
                print("Converting PDF to PNG...")
                images = convert_from_path(
                    str(pdf_file), dpi=300, first_page=1, last_page=1
                )
                if images:
                    images[0].save(output_path, "PNG")
                    print(f"Successfully generated: {output_path}")
                    return True
            else:
                print("PDF file was not created.")
            return False

        except Exception as e:
            print(f"An error occurred: {e}")
            return False


# Tanjah Theme - Iteration 11 (Title Background)
# Colors: #1A6B3A (Green) and #F5B800 (Yellow/Gold)
TEMPLATE = r"""\documentclass[16pt, border=25pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{tikz}

% Define the new colors
\definecolor{mainGreen}{HTML}{1A6B3A}
\definecolor{mainYellow}{HTML}{F5B800}

% Change default font to sans-serif for a cleaner, minimalist look
\renewcommand{\familydefault}{\sfdefault}

\begin{document}
\begin{tikzpicture}
% The main content node
\node[inner sep=0pt] (content) {
    \begin{minipage}{16cm}
    
    % Top-left branding
    {\sffamily\footnotesize\bfseries\textcolor{mainGreen}{TANJAH PHILP}}\par\vspace{0.4cm}

    % Question Box
    % Added a light background to the "Question" text
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainGreen!30!white, 
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainGreen,
        fonttitle=\large\bfseries\sffamily, title=\strut Question, coltitle=mainGreen,
        colbacktitle=mainGreen!8!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainGreen!8!white, colback=mainGreen!8!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    \sffamily {QUESTION_TEXT}
    \end{tcolorbox}
    \vspace{0.4cm}
    
    % The options in a 2-column grid
    \begin{tcbraster}[raster columns=2, raster equal height, raster column skip=0.6cm, raster row skip=0.4cm]
    {OPTIONS}
    \end{tcbraster}
    
    \vspace{0.8cm}
    % Footer
    \begin{minipage}{\linewidth}
        \textcolor{mainGreen!80!black}{%
            \sffamily\bfseries\footnotesize \#YOUR\_FINANCIAL\_ENGINEER \hfill \ttfamily\bfseries @study\_with\_tanjah\_bot%
        }
    \end{minipage}
    \end{minipage}
};
% The watermark overlaid on top of the content
\node[overlay, rotate=45, scale=4.5, opacity=0.06, color=mainGreen] at (content.center) {\fontfamily{pzc}\selectfont\Huge TANJAH};
\end{tikzpicture}
\end{document}"""

if __name__ == "__main__":
    output_img = "test_images/iteration_11_title_bg.png"
    print(f"Attempting to render iteration 11 LaTeX to {output_img}...")

    # Sample Question Data
    sample_question = r"A 50 Hz, 4-pole induction motor runs at a speed of 1440 rpm. Calculate the slip of the motor."

    # Format options as individual minimalist tcolorboxes
    sample_options = r"""\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white, fontupper=\sffamily]
\textbf{\textcolor{mainYellow!90!black}{A}}\hspace{0.3cm} 2\%
\end{tcolorbox}
\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white, fontupper=\sffamily]
\textbf{\textcolor{mainYellow!90!black}{B}}\hspace{0.3cm} 4\%
\end{tcolorbox}
\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white, fontupper=\sffamily]
\textbf{\textcolor{mainYellow!90!black}{C}}\hspace{0.3cm} 5\%
\end{tcolorbox}
\begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow, boxrule=0.3mm, leftrule=1.5mm, arc=1.5mm, drop fuzzy shadow=black!4!white, fontupper=\sffamily]
\textbf{\textcolor{mainYellow!90!black}{D}}\hspace{0.3cm} 3\%
\end{tcolorbox}"""

    # Inject into template
    latex_content = TEMPLATE.replace("{QUESTION_TEXT}", sample_question)
    latex_content = latex_content.replace("{OPTIONS}", sample_options)

    success = render_latex_to_png(latex_content, output_img)
    if success:
        print(f"Done! Check {output_img}")
    else:
        print("Failed to render.")
