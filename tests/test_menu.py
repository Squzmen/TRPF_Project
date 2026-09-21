"""Сквозная проверка меню и сохранения нескольких типов объектов."""

import json
from datetime import date, timedelta

import main
from models import Event
from storage import load_data, save_events, save_plans, save_users


def test_all_menu_items_keep_object_links(monkeypatch, tmp_path, capsys):
    future = date.today() + timedelta(days=7)
    event = Event(1, "Спектакль Гамлет", "театр", future, 12, 1500, 1)
    event_path = tmp_path / "events.json"
    user_path = tmp_path / "users.json"
    plan_path = tmp_path / "plans.json"
    event_path.write_text(json.dumps([event.to_data()], ensure_ascii=False),
                          encoding="utf-8")
    user_path.write_text("[]", encoding="utf-8")
    plan_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(main, "load_data", lambda: load_data(
        event_path, plan_path, user_path
    ))
    monkeypatch.setattr(main, "save_events", lambda events: save_events(
        events, event_path
    ))
    monkeypatch.setattr(main, "save_users", lambda users: save_users(
        users, user_path
    ))
    monkeypatch.setattr(main, "save_plans", lambda plans: save_plans(
        plans, plan_path
    ))
    responses = iter([
        "1", "2", "Гамлет", "3", "театр", "4", "5", "1",
        "Анна", "ошибка", "20", "театр", "2000", "6", "1",
        "Анна", "20", "театр", "2000", "8", "9", "7", "1",
        "8", "9", "10", "Борис", "20", "театр", "2000", "11",
        "12", "Новая выставка", "выставка", future.isoformat(),
        "6", "500", "3", "1", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    main.main()
    output = capsys.readouterr().out
    assert "Введите целое число" in output
    assert "Запись добавлена, ID: 1" in output
    assert "записей: 1" in output and "записей: 0" in output
    assert "отменена" in output
    assert "Посетитель добавлен" in output
    assert "Мероприятие добавлено" in output
    events, users, plans = load_data(event_path, plan_path, user_path)
    assert len(events) == 2 and len(users) == 2
    assert plans[0].is_cancelled
    assert plans[0].user is users[0]
