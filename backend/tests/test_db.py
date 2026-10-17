from db import run_migrations


def test_migrations_are_applied_once(clean_db):
    # The database fixture already ran them, so running again must apply nothing.
    assert run_migrations(clean_db) == []
