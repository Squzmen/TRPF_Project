"""Перенос данных проекта из JSON-файлов в таблицы SQLite.

Запуск из корня проекта: python -m db.import_json
Скрипт создаёт таблицы (если их нет), очищает их и заново загружает
содержимое data/events.json, data/users.json и data/plans.json.
"""

import json

from db.database import BASE_DIR, create_schema, get_connection

EVENTS_FILE = BASE_DIR / "data" / "events.json"
USERS_FILE = BASE_DIR / "data" / "users.json"
PLANS_FILE = BASE_DIR / "data" / "plans.json"


def load_json(filename):
    """Прочитать список записей из JSON-файла в кодировке UTF-8."""
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def clear_tables(conn):
    """Удалить старые данные: сначала зависимая таблица plans."""
    conn.execute("DELETE FROM plans")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM events")


def import_events(conn):
    """Загрузить мероприятия; категория хранится строчными буквами."""
    events = load_json(EVENTS_FILE)
    conn.executemany(
        """
        INSERT INTO events (
            id, name, category, event_date,
            age_limit, ticket_price, capacity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                event["id"],
                event["name"],
                event["category"].strip().lower(),
                event["event_date"],
                event["age_limit"],
                event["ticket_price"],
                event["capacity"],
            )
            for event in events
        ],
    )


def import_users(conn):
    """Загрузить посетителей; категория хранится строчными буквами."""
    users = load_json(USERS_FILE)
    conn.executemany(
        """
        INSERT INTO users (id, name, age, preferred_category, budget)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                user["id"],
                user["name"],
                user["age"],
                user["preferred_category"].strip().lower(),
                user["budget"],
            )
            for user in users
        ],
    )


def import_plans(conn):
    """Загрузить записи; признак отмены из JSON хранится как 0 или 1."""
    plans = load_json(PLANS_FILE)
    conn.executemany(
        """
        INSERT INTO plans (id, event_id, user_id, is_cancelled)
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                plan["id"],
                plan["event_id"],
                plan["user_id"],
                int(plan["is_cancelled"]),
            )
            for plan in plans
        ],
    )


def main(db_path=None):
    """Создать схему и перенести данные одной транзакцией."""
    conn = get_connection(db_path)
    try:
        create_schema(conn)
        clear_tables(conn)
        import_events(conn)
        import_users(conn)
        import_plans(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
