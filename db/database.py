"""Подключение к базе данных SQLite и вспомогательные функции."""

import sqlite3
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "culture.sqlite"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"


def get_connection(db_path=None):
    """Открыть соединение и включить проверку внешних ключей."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn, schema_path=SCHEMA_PATH):
    """Создать таблицы, выполнив SQL-команды из файла схемы."""
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def rows_with_dates(rows, *date_fields):
    """Преобразовать строки sqlite3.Row в словари и ISO-даты в date.

    SQLite хранит даты как текст ГГГГ-ММ-ДД, а фильтр шаблона date
    работает только с объектами date.
    """
    result = []
    for row in rows:
        item = dict(row)
        for field in date_fields:
            item[field] = date.fromisoformat(item[field])
        result.append(item)
    return result
