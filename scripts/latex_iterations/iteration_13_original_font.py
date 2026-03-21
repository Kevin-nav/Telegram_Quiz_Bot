from src.domains.question_bank.latex_renderer import (
    build_question_latex,
    render_latex_to_png,
)

if __name__ == "__main__":
    output_img = "test_images/iteration_13_original_font.png"
    print(f"Attempting to render iteration 13 LaTeX to {output_img}...")

    # Sample Question Data - A long differential equation question
    sample_question = r"The solution of the differential equation $\frac{dy}{dx}+Py=Q$ where P and Q are the function of x is"

    sample_options = [
        r"$\displaystyle y=\int Qe^{\int pdx}dx+C$",
        r"$\displaystyle y=\int Qe^{-\int pdx}dx+C$",
        r"$\displaystyle ye^{\int pdx}=\int Qe^{\int pdx}dx+C$",
        r"$\displaystyle ye^{\int pdx}=\int Qe^{-\int pdx}dx+C$",
    ]

    latex_content = build_question_latex(sample_question, sample_options)

    success = render_latex_to_png(latex_content, output_img)
    if success:
        print(f"Done! Check {output_img}")
    else:
        print("Failed to render.")
