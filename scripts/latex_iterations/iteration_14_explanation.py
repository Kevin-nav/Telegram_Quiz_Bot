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


# Tanjah Theme - Iteration 14 (Explanation style)
# Colors: #1A6B3A (Green) and #F5B800 (Yellow/Gold)
# For the explanation, we want to show the correct option text (no A/B/C/D) and the explanation.
TEMPLATE = r"""\documentclass[16pt, border=25pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{tikz}

% Define the new colors
\definecolor{mainGreen}{HTML}{1A6B3A}
\definecolor{mainYellow}{HTML}{F5B800}

\begin{document}
\begin{tikzpicture}
% The main content node
\node[inner sep=0pt] (content) {
    \begin{minipage}{16cm}
    
    % Top-left branding
    {\footnotesize\bfseries\textcolor{mainGreen}{TANJAH PHILP}}\par\vspace{0.4cm}

    % Answer Box (Highlighting the correct answer text)
    % Using the Yellow theme here as it represents the options
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainYellow!40!white, 
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainYellow,
        fonttitle=\large\bfseries, title=\strut Correct Answer, coltitle=mainYellow!80!black,
        colbacktitle=mainYellow!15!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainYellow!15!white, colback=mainYellow!15!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    {CORRECT_OPTION_TEXT}
    \end{tcolorbox}
    \vspace{0.6cm}
    
    % Explanation Box
    % Using the main Green theme for the detailed explanation
    \begin{tcolorbox}[enhanced, colback=white, colframe=mainGreen!30!white, 
        boxrule=0.4mm, leftrule=2.5mm, arc=2.5mm, colframe=mainGreen,
        fonttitle=\large\bfseries, title=\strut Explanation, coltitle=mainGreen,
        colbacktitle=mainGreen!8!white, attach boxed title to top left={yshift=-3mm, xshift=4mm},
        boxed title style={boxrule=0pt, colframe=mainGreen!8!white, colback=mainGreen!8!white, arc=1.5mm, size=small},
        drop fuzzy shadow=black!6!white]
    {EXPLANATION_TEXT}
    \end{tcolorbox}
    
    \vspace{0.8cm}
    % Footer
    \begin{minipage}{\linewidth}
        \textcolor{mainGreen!80!black}{%
            \bfseries\footnotesize \#YOUR\_FINANCIAL\_ENGINEER \hfill \ttfamily\bfseries @study\_with\_tanjah\_bot%
        }
    \end{minipage}
    \end{minipage}
};
% The watermark overlaid on top of the content
\node[overlay, rotate=45, scale=4.5, opacity=0.06, color=mainGreen] at (content.center) {\fontfamily{pzc}\selectfont\Huge TANJAH};
\end{tikzpicture}
\end{document}"""

if __name__ == "__main__":
    output_img = "test_images/iteration_14_explanation.png"
    print(f"Attempting to render iteration 14 LaTeX to {output_img}...")

    # Sample Data - Assuming option C was correct from previous example
    correct_option = r"$\displaystyle ye^{\int pdx}=\int Qe^{\int pdx}dx+C$"

    explanation = r"This is a first-order linear differential equation. To solve it, we must first find the integrating factor, which is given by $e^{\int P dx}$. \\\\ Multiplying both sides of the equation by this integrating factor and then integrating with respect to $x$ yields the correct solution form."

    # Inject into template
    latex_content = TEMPLATE.replace("{CORRECT_OPTION_TEXT}", correct_option)
    latex_content = latex_content.replace("{EXPLANATION_TEXT}", explanation)

    success = render_latex_to_png(latex_content, output_img)
    if success:
        print(f"Done! Check {output_img}")
    else:
        print("Failed to render.")
