from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
# Arbitrary key for the advisory lock, so two processes never migrate at the same time.
MIGRATION_LOCK_KEY = 727274


def connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def run_migrations(database_url: str) -> list[str]:
    """Apply every migrations/*.sql file that has not run yet. Returns the names applied now."""
    applied_now = []
    with connect(database_url) as conn:
        with conn.transaction():
            conn.execute("select pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))
            conn.execute(
                """
                create table if not exists schema_migrations (
                    version text primary key,
                    applied_at timestamptz not null default now()
                )
                """
            )
            done = {row[0] for row in conn.execute("select version from schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                conn.execute(path.read_text())
                conn.execute("insert into schema_migrations (version) values (%s)", (path.name,))
                applied_now.append(path.name)
    return applied_now
