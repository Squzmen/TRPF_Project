"""Проверки восстановления JSON и обработки поврежденных данных."""

import json

import pytest

from storage import StorageError, load_data, save_plans
from test_plans import EVENT


def test_save_and_reload(tmp_path):
    events_file = tmp_path / "events.json"
    plans_file = tmp_path / "plans.json"
    events_file.write_text(json.dumps([EVENT], ensure_ascii=False),
                           encoding="utf-8")
    plans = [{"id": 1, "event_id": 1, "user_name": "Анна",
              "user_age": 20, "preferred_category": "театр",
              "budget": 2000}]
    save_plans(plans, plans_file)
    assert load_data(events_file, plans_file) == ([EVENT], plans)


def test_invalid_json_does_not_silently_reset(tmp_path):
    events_file = tmp_path / "events.json"
    plans_file = tmp_path / "plans.json"
    events_file.write_text("[broken", encoding="utf-8")
    plans_file.write_text("[]", encoding="utf-8")
    with pytest.raises(StorageError, match="Ошибка чтения"):
        load_data(events_file, plans_file)


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(StorageError, match="Ошибка чтения"):
        load_data(tmp_path / "missing.json", tmp_path / "plans.json")


def test_save_failure_is_reported(tmp_path):
    path = tmp_path / "missing" / "plans.json"
    with pytest.raises(StorageError, match="Ошибка записи"):
        save_plans([], path)
    assert not path.exists()


def test_unknown_event_reference_is_reported(tmp_path):
    events_file = tmp_path / "events.json"
    plans_file = tmp_path / "plans.json"
    events_file.write_text(json.dumps([EVENT], ensure_ascii=False),
                           encoding="utf-8")
    plans_file.write_text(json.dumps([{
        "id": 1, "event_id": 999, "user_name": "Анна", "user_age": 20,
        "preferred_category": "театр", "budget": 2000,
    }]), encoding="utf-8")
    with pytest.raises(StorageError, match="Некорректная запись"):
        load_data(events_file, plans_file)
