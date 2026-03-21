from src.domains.question_bank.latex_renderer import (
    build_explanation_latex,
    build_latex_option_variants,
    build_question_latex,
    build_variant_order_maps,
)


def test_build_latex_option_variants_returns_four_distinct_orders():
    variants = build_latex_option_variants(["A", "B", "C", "D"])

    assert len(variants) == 4
    assert len({tuple(variant) for variant in variants}) == 4


def test_build_variant_order_maps_matches_expected_shape():
    variant_maps = build_variant_order_maps(4)

    assert variant_maps == [
        [0, 1, 2, 3],
        [1, 0, 3, 2],
        [2, 3, 0, 1],
        [3, 2, 1, 0],
    ]


def test_question_and_explanation_templates_include_supplied_content():
    question_latex = build_question_latex("Solve $x+1=2$", ["1", "2", "3", "4"])
    explanation_latex = build_explanation_latex("2", "Because $x=1$.")

    assert "Solve $x+1=2$" in question_latex
    assert "\\textcolor{mainYellow!90!black}{A}" in question_latex
    assert "Because $x=1$." in explanation_latex
    assert "Correct Answer" in explanation_latex
