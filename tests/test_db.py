"""Проверки слоя SQLite: схема, импорт из JSON и файл запросов (ПР7)."""

import inspect
import json
import re
import sqlite3

import pytest

import catalog.views
import planner.views
from db import import_json
from db.database import (
    BASE_DIR, DB_PATH, get_connection, rows_with_dates,
)

QUERIES_FILE = BASE_DIR / "sql" / "queries.sql"


@pytest.fixture
def database(tmp_path):
    """Временная база, заполненная из JSON-файлов проекта."""
    path = tmp_path / "test.sqlite"
    import_json.main(path)
    return path


def scalar(path, query):
    """Выполнить запрос и вернуть единственное значение."""
    conn = get_connection(path)
    try:
        return conn.execute(query).fetchone()[0]
    finally:
        conn.close()


def read_queries():
    """Вернуть SQL-запросы из sql/queries.sql без комментариев."""
    text = QUERIES_FILE.read_text(encoding="utf-8")
    code = re.sub(r"--[^\n]*", "", text)
    return [part.strip() for part in code.split(";") if part.strip()]


def test_schema_has_tables_and_foreign_keys(database):
    """Созданы три таблицы; plans ссылается на events и users."""
    conn = get_connection(database)
    try:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        keys = conn.execute("PRAGMA foreign_key_list(plans)").fetchall()
        primary = conn.execute("PRAGMA table_info(events)").fetchall()
    finally:
        conn.close()
    assert tables == {"events", "users", "plans"}
    assert {(key[2], key[3], key[4]) for key in keys} == {
        ("events", "event_id", "id"),
        ("users", "user_id", "id"),
    }
    assert [column[1] for column in primary if column[5]] == ["id"]


def test_import_moves_all_json_records(database):
    """Число записей в таблицах равно числу записей в JSON-файлах."""
    for table, path in (("events", import_json.EVENTS_FILE),
                        ("users", import_json.USERS_FILE),
                        ("plans", import_json.PLANS_FILE)):
        expected = len(json.loads(path.read_text(encoding="utf-8")))
        assert scalar(database, f"SELECT COUNT(*) FROM {table}") == expected


def test_import_converts_cancel_flag_to_integer(database):
    """Признак is_cancelled из JSON хранится как 0 или 1."""
    plans = json.loads(
        import_json.PLANS_FILE.read_text(encoding="utf-8")
    )
    cancelled = sum(plan["is_cancelled"] for plan in plans)
    query = "SELECT COUNT(*) FROM plans WHERE is_cancelled = 1"
    assert scalar(database, query) == cancelled


def test_import_can_be_repeated(database):
    """Повторный импорт не дублирует данные и не вызывает ошибок."""
    import_json.main(database)
    events = json.loads(
        import_json.EVENTS_FILE.read_text(encoding="utf-8")
    )
    assert scalar(database, "SELECT COUNT(*) FROM events") == len(events)


def test_foreign_keys_are_enforced(database):
    """Запись с несуществующим мероприятием отклоняется базой."""
    conn = get_connection(database)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO plans (id, event_id, user_id) "
                "VALUES (?, ?, ?)",
                [999, 12345, 1],
            )
    finally:
        conn.close()


@pytest.mark.parametrize("query, params", [
    ("INSERT INTO events (id, name, category, event_date, age_limit, "
     "ticket_price, capacity) VALUES (?, ?, ?, ?, ?, ?, ?)",
     [99, "Тест", "театр", "2030-01-01", 0, -1, 1]),
    ("INSERT INTO plans (id, event_id, user_id, is_cancelled) "
     "VALUES (?, ?, ?, ?)", [99, 1, 1, 2]),
])
def test_check_constraints(database, query, params):
    """Ограничения CHECK не пропускают некорректные значения."""
    conn = get_connection(database)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(query, params)
    finally:
        conn.close()


def test_failed_import_keeps_previous_data(database, tmp_path, monkeypatch):
    """При ошибке импорт откатывается и старые данные сохраняются."""
    broken = tmp_path / "plans.json"
    broken.write_text(
        json.dumps([{"id": 1, "event_id": 1, "user_id": 999,
                     "is_cancelled": False}]),
        encoding="utf-8",
    )
    before = scalar(database, "SELECT COUNT(*) FROM plans")
    monkeypatch.setattr(import_json, "PLANS_FILE", broken)
    with pytest.raises(sqlite3.IntegrityError):
        import_json.main(database)
    assert scalar(database, "SELECT COUNT(*) FROM plans") == before
    assert scalar(database, "SELECT COUNT(*) FROM events") > 0


def test_project_database_file_exists_and_filled():
    """Файл базы проекта создан и содержит все три таблицы с данными."""
    assert DB_PATH.exists()
    for table in ("events", "users", "plans"):
        assert scalar(DB_PATH, f"SELECT COUNT(*) FROM {table}") > 0


def test_queries_file_covers_required_kinds():
    """В queries.sql не менее 10 запросов каждого требуемого вида."""
    queries = [query.upper() for query in read_queries()]
    assert len(queries) >= 10
    assert sum(" WHERE " in query for query in queries) >= 2
    assert sum(" JOIN " in query for query in queries) >= 2
    assert sum("COUNT(" in query for query in queries) >= 2
    assert sum("GROUP BY" in query for query in queries) >= 2
    assert sum("HAVING" in query for query in queries) >= 1


def test_every_saved_query_runs(database):
    """Каждый сохранённый запрос выполняется без ошибок."""
    conn = get_connection(database)
    try:
        for query in read_queries():
            assert conn.execute(query).fetchall() is not None, query
    finally:
        conn.close()


@pytest.mark.parametrize("module", [catalog.views, planner.views])
def test_views_use_parameters_not_string_formatting(module):
    """В представлениях значения передаются через ?, а не через f-строки."""
    source = inspect.getsource(module)
    assert "row_factory = sqlite3.Row" in source
    assert not re.search(r'f"""\s*SELECT', source)
    assert not re.search(r"execute\(\s*f", source)
    assert "%s" not in source


def test_rows_with_dates_converts_iso_strings(database):
    """ISO-даты из SQLite превращаются в объекты date."""
    conn = get_connection(database)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT id, event_date FROM events").fetchall()
    finally:
        conn.close()
    converted = rows_with_dates(rows, "event_date")
    assert all(hasattr(item["event_date"], "year") for item in converted)
    assert [item["id"] for item in converted] == [row["id"] for row in rows]
