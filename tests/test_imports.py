def test_app_import():
    from src.main import app

    assert app is not None
