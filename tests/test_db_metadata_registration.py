def test_canonical_database_import_registers_question_bank_tables():
    from src.database import Base

    table_names = set(Base.metadata.tables)

    assert "question_bank" in table_names
    assert "question_asset_variants" in table_names
    assert "student_course_state" in table_names
    assert "question_attempts" in table_names
