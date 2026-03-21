from src.domains.question_bank.latex_renderer import (
    build_explanation_latex,
    render_latex_to_png,
)

if __name__ == "__main__":
    output_img = "test_images/iteration_14_explanation.png"
    print(f"Attempting to render iteration 14 LaTeX to {output_img}...")

    # Sample Data - Assuming option C was correct from previous example
    correct_option = r"$\displaystyle ye^{\int pdx}=\int Qe^{\int pdx}dx+C$"

    explanation = r"This is a first-order linear differential equation. To solve it, we must first find the integrating factor, which is given by $e^{\int P dx}$. \\\\ Multiplying both sides of the equation by this integrating factor and then integrating with respect to $x$ yields the correct solution form."

    latex_content = build_explanation_latex(correct_option, explanation)

    success = render_latex_to_png(latex_content, output_img)
    if success:
        print(f"Done! Check {output_img}")
    else:
        print("Failed to render.")
