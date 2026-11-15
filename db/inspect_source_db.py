"""Инспекция исходной базы ПР7 перед переносом в Django ORM (ПР9).

Запуск из корня проекта: python -m db.inspect_source_db
Скрипт только читает data/culture.sqlite: выводит таблицы, столбцы,
количество записей и проверяет, что внешние ключи plans ссылаются на
существующие мероприятия и посетителей.
"""

import sqlite3

from db.database import DB_PATH

TABLES = ("events", "users", "plans")


def inspect(source=DB_PATH):
    """Вернуть сведения о таблицах и висячих ссылках исходной базы."""
    if not source.exists():
        raise FileNotFoundError(f"Исходная база не найдена: {source}")
    report = {}
    with sqlite3.connect(source) as connection:
        connection.row_factory = sqlite3.Row
        for table in TABLES:
            columns = [
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            report[table] = {"columns": columns, "count": count}
        report["broken_links"] = connection.execute(
            """
            SELECT COUNT(*)
            FROM plans AS p
            LEFT JOIN events AS e ON p.event_id = e.id
            LEFT JOIN users AS u ON p.user_id = u.id
            WHERE e.id IS NULL OR u.id IS NULL
            """
        ).fetchone()[0]
        report["cancel_values"] = sorted(
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT is_cancelled FROM plans"
            )
        )
    return report


def main():
    report = inspect()
    for table in TABLES:
        info = report[table]
        print(f"{table}: {info['count']} записей; столбцы: "
              f"{', '.join(info['columns'])}")
    print(f"Висячих ссылок в plans: {report['broken_links']}")
    print(f"Значения is_cancelled: {report['cancel_values']}")


if __name__ == "__main__":
    main()
