"""Truncate user/account/progress tables only. Keeps system catalogs and alembic_version."""

from sqlalchemy import text

from app.db.session import engine

USER_TABLES = [
    "user_rewards",
    "habit_tracker",
    "child_habit_fridge_inventory",
    "child_habit_preferences",
    "child_simulation_progress",
    "child_island_progress",
    "learner_permit_badges",
    "email_verification_codes",
    "voucher_redemptions",
    "user_activity",
    "learner_permits",
    "classrooms",
    "schools",
    "families",
    "users",
]

SYSTEM_TABLES = [
    "islands",
    "locations",
    "simulations",
    "simulation_answers",
    "habits",
    "habit_steps",
    "habit_step_options",
    "prize_items",
    "comic_pages",
    "rewards",
    "pricing_plans",
    "vouchers",
    "voucher_pricing_plans",
]


def main() -> None:
    sql = f"TRUNCATE TABLE {', '.join(USER_TABLES)} RESTART IDENTITY CASCADE"
    with engine.begin() as conn:
        conn.execute(text(sql))

    print("User data wipe complete.")
    print("User tables (expect 0):")
    with engine.connect() as conn:
        for table in USER_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")

        print("System tables (preserved):")
        for table in SYSTEM_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
