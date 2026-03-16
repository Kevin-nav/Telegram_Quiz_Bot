def test_latex_object_key_generation():
    from src.infra.r2.storage import build_latex_object_key

    key = build_latex_object_key("math101", "q42", "abc123")

    assert key == "latex/math101/q42/abc123.png"
