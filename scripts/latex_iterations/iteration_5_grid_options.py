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


# Adjusting the layout to use a fixed width minipage (16cm) for consistent image widths.
# Using tcbraster to create a 2x2 grid of tcolorboxes for the options.
TEMPLATE = r"""\documentclass[16pt, border=10pt]{standalone}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath}\usepackage{amsfonts}
\usepackage{amssymb}\usepackage{mhchem}\usepackage{xcolor}
\usepackage{textgreek}\DeclareUnicodeCharacter{2081}{\textsubscript{1}}\DeclareUnicodeCharacter{2082}{\textsubscript{2}}
\usepackage[most]{tcolorbox}\usepackage{tikz}

\definecolor{questionbg}{rgb}{0.95, 0.95, 0.98}
\definecolor{optionbg}{rgb}{0.98, 0.98, 0.99}

\begin{document}
\begin{tikzpicture}
% The main content node
\node[inner sep=0pt] (content) {
    \begin{minipage}{16cm}
    \begin{tcolorbox}[colback=questionbg, colframe=black!50!blue, title=\textbf{Question}, fonttitle=\Large\bfseries]
    {QUESTION_TEXT}
    \end{tcolorbox}
    \vspace{0.2cm}
    
    % The options in a 2-column grid
    \begin{tcbraster}[raster columns=2, raster equal height, raster column skip=0.4cm, raster row skip=0.4cm]
    {OPTIONS}
    \end{tcbraster}
    \end{minipage}
};
% The watermark overlaid on top of the content
\node[overlay, rotate=45, scale=6, opacity=0.08, color=black] at (content.center) {\textbf{Adarkwa}};
\end{tikzpicture}
\end{document}"""

if __name__ == "__main__":
    output_img = "test_images/iteration_5_grid.png"
    print(f"Attempting to render iteration 5 LaTeX to {output_img}...")

    # Sample Question Data
    sample_question = r"A 50 Hz, 4-pole induction motor runs at a speed of 1440 rpm. Calculate the slip of the motor."

    # Format options as individual tcolorboxes
    sample_options = r"""\begin{tcolorbox}[colback=optionbg, colframe=black!40!blue, boxrule=0.5mm, title=\textbf{A)}]
2\%
\end{tcolorbox}
\begin{tcolorbox}[colback=optionbg, colframe=black!40!blue, boxrule=0.5mm, title=\textbf{B)}]
4\%
\end{tcolorbox}
\begin{tcolorbox}[colback=optionbg, colframe=black!40!blue, boxrule=0.5mm, title=\textbf{C)}]
5\%
\end{tcolorbox}
\begin{tcolorbox}[colback=optionbg, colframe=black!40!blue, boxrule=0.5mm, title=\textbf{D)}]
3\%
\end{tcolorbox}"""

    # Inject into template
    latex_content = TEMPLATE.replace("{QUESTION_TEXT}", sample_question)
    latex_content = latex_content.replace("{OPTIONS}", sample_options)

    success = render_latex_to_png(latex_content, output_img)
    if success:
        print(f"Done! Check {output_img}")
    else:
        print("Failed to render.")
