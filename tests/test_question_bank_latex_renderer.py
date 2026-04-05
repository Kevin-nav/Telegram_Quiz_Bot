from src.bot.runtime_config import DEFAULT_BOT_THEMES
from src.domains.question_bank.latex_renderer import (
    VARIANT_ORDERS,
    build_explanation_latex,
    build_latex_option_variants,
    build_question_latex,
    build_variant_order_maps,
    escape_latex_text,
)


def test_build_latex_option_variants_returns_four_distinct_orders():
    variants = build_latex_option_variants(["A", "B", "C", "D"])

    assert len(variants) == 4
    assert len({tuple(variant) for variant in variants}) == 4


def test_build_variant_order_maps_matches_expected_shape():
    variant_maps = build_variant_order_maps(4)

    assert variant_maps == [list(order) for order in VARIANT_ORDERS]


def test_build_latex_option_variants_supports_two_options_with_rotations():
    variants = build_latex_option_variants(["True", "False"])

    assert variants == [["True", "False"], ["False", "True"]]


def test_build_variant_order_maps_supports_five_options_with_rotations():
    variant_maps = build_variant_order_maps(5)

    assert variant_maps == [
        [0, 1, 2, 3, 4],
        [1, 2, 3, 4, 0],
        [2, 3, 4, 0, 1],
        [3, 4, 0, 1, 2],
        [4, 0, 1, 2, 3],
    ]


def test_question_and_explanation_templates_include_supplied_content():
    question_latex = build_question_latex("Solve $x+1=2$", ["1", "2", "3", "4"])
    explanation_latex = build_explanation_latex("2", "Because $x=1$.")

    assert "Solve $x+1=2$" in question_latex
    assert "\\textcolor{mainYellow!90!black}{A}" in question_latex
    assert "Because $x=1$." in explanation_latex
    assert "Correct Answer" in explanation_latex


def test_bot_theme_changes_question_and_explanation_watermark_and_colors():
    adarkwa_theme = DEFAULT_BOT_THEMES["adarkwa"]

    question_latex = build_question_latex(
        "Solve $x+1=2$",
        ["1", "2", "3", "4"],
        bot_theme=adarkwa_theme,
    )
    explanation_latex = build_explanation_latex(
        "1",
        "Because $x=1$.",
        bot_theme=adarkwa_theme,
    )

    assert "\\textbf{ADARKWA}" in question_latex
    assert "\\textbf{ADARKWA}" in explanation_latex
    assert "123B7A" in question_latex
    assert "123B7A" in explanation_latex


def test_escape_latex_text_escapes_literal_dollars_and_preserves_math_spans():
    escaped = escape_latex_text(
        "Cost is $9,537 and $z + \\frac{1}{z}$ is real while $1 + \\omega + \\omega^2 = 0$."
    )

    assert (
        escaped
        == r"Cost is \$9,537 and $z + \frac{1}{z}$ is real while $1 + \omega + \omega^2 = 0$."
    )


def test_escape_latex_text_repairs_matrix_row_separators_before_digits():
    escaped = escape_latex_text(r"$\begin{matrix}1&2\3&4\end{matrix}$")

    assert escaped == r"$\begin{matrix}1&2\\3&4\end{matrix}$"


def test_escape_latex_text_replaces_plain_text_unicode_math_symbols():
    escaped = escape_latex_text("μ = Φ/A ≈ π and ε")

    assert escaped == (
        r"\ensuremath{\mu} = \ensuremath{\Phi}/A "
        r"\ensuremath{\approx} \ensuremath{\pi} and \ensuremath{\epsilon}"
    )
