"""Проверки сценария меню и устойчивости ввода."""

import json
from datetime import date, timedelta

import main
from storage import save_plans
from test_plans import EVENT


def test_menu_create_list_cancel_and_statistics(monkeypatch, tmp_path,
                                                capsys):
    plans_path = tmp_path / "plans.json"
    plans_path.write_text("[]\n", encoding="utf-8")
    event = {**EVENT, "event_date": (
        date.today() + timedelta(days=7)
    ).isoformat()}
    monkeypatch.setattr(main, "load_data", lambda: ([event], []))
    monkeypatch.setattr(main, "save_plans",
                        lambda plans: save_plans(plans, plans_path))
    responses = iter([
        "1", "2", "Гамлет", "3", "театр", "4", "5", "1",
        "Анна", "нет", "20", "театр", "2000", "6", "1",
        "Анна", "20", "театр", "2000", "8", "9", "7", "1", "9", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    main.main()
    output = capsys.readouterr().out
    assert "Введите целое число" in output
    assert "Запись добавлена, ID: 1" in output
    assert "записей: 1" in output
    assert "Запись отменена" in output
    assert "записей: 0" in output
    assert json.loads(plans_path.read_text(encoding="utf-8")) == []
