"""Truncate all application tables (full data wipe). Keeps schema and alembic_version."""

from sqlalchemy import text

from app.db.session import engine

TABLES = [
    "user_rewards",
    "habit_tracker",
    "user_activity",
    "email_verification_codes",
    "voucher_redemptions",
    "learner_permit_badges",
    "learner_permits",
    "simulation_answers",
    "habits",
    "prize_items",
    "simulations",
    "comic_pages",
    "locations",
    "islands",
    "voucher_pricing_plans",
    "vouchers",
    "rewards",
    "pricing_plans",
    "classrooms",
    "schools",
    "families",
    "users",
]


def main() -> None:
    sql = f"TRUNCATE TABLE {', '.join(TABLES)} RESTART IDENTITY CASCADE"
    with engine.begin() as conn:
        conn.execute(text(sql))
        rows = conn.execute(
            text(
                """
                SELECT c.relname,
                       (SELECT COUNT(*) FROM pg_catalog.pg_class c2
                        JOIN pg_catalog.pg_namespace n ON n.oid = c2.relnamespace
                        WHERE c2.relname = c.relname AND n.nspname = 'public'
                        AND c2.relkind = 'r') AS exists_flag
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                  AND c.relname = ANY(:tables)
                ORDER BY c.relname
                """
            ),
            {"tables": TABLES},
        ).fetchall()

    print("Full wipe complete.")
    print("Verifying row counts:")
    with engine.connect() as conn:
        for table in TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
