"""Проверки сериализации, миграции и целостности JSON."""

import json

import pytest

from models import Plan
from storage import (
    StorageError, load_data, save_events, save_plans, save_users,
)


def files(tmp_path, events, users=None, plans=None):
    """Подготовить три изолированных JSON-файла для теста."""
    paths = [tmp_path / name for name in (
        "events.json", "users.json", "plans.json"
    )]
    for path, records in zip(paths, (events, users or [], plans or [])):
        path.write_text(json.dumps(records, ensure_ascii=False),
                        encoding="utf-8")
    return paths


def test_objects_survive_save_and_reload(tmp_path, event, user):
    event_path, user_path, plan_path = files(tmp_path, [], [], [])
    save_events([event], event_path)
    save_users([user], user_path)
    save_plans([Plan(1, event, user, True)], plan_path)
    events, users, plans = load_data(event_path, plan_path, user_path)
    assert plans[0].event is events[0]
    assert plans[0].user is users[0]
    assert plans[0].is_cancelled
    assert json.loads(plan_path.read_text(encoding="utf-8")) == [
        {"id": 1, "event_id": 1, "user_id": 1, "is_cancelled": True}
    ]


def test_legacy_pr2_plan_loads_without_mutating_files(tmp_path, event):
    legacy = {
        "id": 3, "event_id": 1, "user_name": "Анна",
        "user_age": 20, "preferred_category": "театр", "budget": 2000,
    }
    paths = files(tmp_path, [event.to_data()], [], [legacy])
    events, users, plans = load_data(paths[0], paths[2], paths[1])
    assert len(users) == 1
    assert plans[0].user is users[0]
    assert plans[0].event is events[0]
    assert json.loads(paths[2].read_text(encoding="utf-8")) == [legacy]
    save_users(users, paths[1])
    _, again_users, _ = load_data(paths[0], paths[2], paths[1])
    assert len(again_users) == 1
    save_plans(plans, paths[2])
    _, reloaded_users, reloaded_plans = load_data(
        paths[0], paths[2], paths[1]
    )
    assert reloaded_plans[0].user is reloaded_users[0]


def test_bad_json_and_missing_file_are_reported(tmp_path, event):
    paths = files(tmp_path, [event.to_data()])
    paths[0].write_text("[broken", encoding="utf-8")
    with pytest.raises(StorageError, match="Ошибка чтения"):
        load_data(paths[0], paths[2], paths[1])
    with pytest.raises(StorageError, match="Ошибка чтения"):
        load_data(tmp_path / "missing.json", paths[2], paths[1])


def test_unknown_user_reference_fails_without_data_loss(tmp_path, event):
    plan = {"id": 1, "event_id": 1, "user_id": 999,
            "is_cancelled": False}
    paths = files(tmp_path, [event.to_data()], [], [plan])
    with pytest.raises(StorageError, match="Некорректные данные"):
        load_data(paths[0], paths[2], paths[1])
    assert json.loads(paths[2].read_text(encoding="utf-8")) == [plan]


def test_overcapacity_and_duplicate_ids_are_rejected(tmp_path, event, user):
    active = {"id": 1, "event_id": 1, "user_id": 1,
              "is_cancelled": False}
    other = {**user.to_data(), "id": 2, "name": "Борис"}
    paths = files(tmp_path, [event.to_data()], [user.to_data(), other],
                  [active, {**active, "id": 2, "user_id": 2}])
    with pytest.raises(StorageError, match="вместимость"):
        load_data(paths[0], paths[2], paths[1])
    paths = files(tmp_path, [event.to_data(), event.to_data()])
    with pytest.raises(StorageError, match="Повторяющийся ID"):
        load_data(paths[0], paths[2], paths[1])


def test_failed_save_does_not_create_target(tmp_path):
    path = tmp_path / "missing" / "plans.json"
    with pytest.raises(StorageError, match="Ошибка записи"):
        save_plans([], path)
    assert not path.exists()
