"""Консольное меню системы планирования культурного досуга."""

from datetime import date

from events import (
    filter_events, find_event, get_event_date_status, search_events,
    sort_events,
)
from plans import (
    cancel_plan, create_plan, find_plan, plan_recommendation,
    plan_statistics, remaining_seats,
)
from storage import StorageError, load_data, save_plans
from utils import input_float, input_int, input_nonempty


def show_events(events: list[dict], plans: list[dict]) -> None:
    """Показать каталог мероприятий с числом оставшихся мест."""
    if not events:
        print("Мероприятий не найдено.")
        return
    for event in events:
        print(
            f"{event['id']}. {event['name']} | {event['category']} | "
            f"{event['event_date']} | {event['ticket_price']:.2f} руб. | "
            f"мест: {remaining_seats(plans, event)}"
        )


def show_plans(plans: list[dict], events: list[dict]) -> None:
    """Показать созданные записи в план досуга."""
    if not plans:
        print("Планов пока нет.")
        return
    for plan in plans:
        event = find_event(events, plan["event_id"])
        print(
            f"{plan['id']}. {plan['user_name']} — {event['name']} "
            f"({event['event_date']})"
        )


def ask_event(events: list[dict]) -> dict | None:
    """Запросить существующее мероприятие по его ID."""
    event_id = input_int("ID мероприятия: ", minimum=1)
    event = find_event(events, event_id)
    if event is None:
        print("Мероприятие не найдено.")
    return event


def ask_user() -> tuple[str, int, str, float]:
    """Запросить данные посетителя для проверок из ПР1."""
    name = input_nonempty("Имя: ")
    age = input_int("Возраст: ", minimum=0)
    category = input_nonempty("Интересующая категория: ")
    budget = input_float("Бюджет (руб.): ", minimum=0)
    return name, age, category, budget


def handle_check(events: list[dict], plans: list[dict],
                 save: bool = False) -> None:
    """Проверить мероприятие и, если нужно, записать посетителя."""
    event = ask_event(events)
    if event is None:
        return
    name, age, category, budget = ask_user()
    event_day = date.fromisoformat(event["event_date"])
    print(f"Статус даты: {get_event_date_status(event_day, date.today())}")
    status = plan_recommendation(plans, event, age, category, budget)
    print(status)
    if not save:
        return
    try:
        plan = create_plan(plans, event, name, age, category, budget)
    except ValueError as error:
        print(f"Запись не создана: {error}")
        return
    try:
        save_plans(plans)
    except StorageError as error:
        plans.remove(plan)
        print(f"Запись не сохранена: {error}")
    else:
        print(f"Запись добавлена, ID: {plan['id']}.")


def handle_cancel(plans: list[dict]) -> None:
    """Отменить запись и сохранить изменение на диске."""
    plan_id = input_int("ID записи: ", minimum=1)
    plan = find_plan(plans, plan_id)
    if plan is None:
        print("Запись не найдена.")
        return
    position = plans.index(plan)
    cancel_plan(plans, plan_id)
    try:
        save_plans(plans)
    except StorageError as error:
        plans.insert(position, plan)
        print(f"Отмена не сохранена: {error}")
    else:
        print("Запись отменена.")


def main() -> None:
    """Загрузить данные и выполнять действия в цикле до выхода."""
    try:
        events, plans = load_data()
    except StorageError as error:
        print(f"Не удалось загрузить данные: {error}")
        return

    print("Система планирования культурного досуга — ПР2")
    while True:
        print(
            "\n1. Мероприятия  2. Поиск  3. Фильтр по категории\n"
            "4. Сортировка по цене  5. Проверить мероприятие\n"
            "6. Добавить в план  7. Отменить запись\n"
            "8. Показать планы  9. Статистика  0. Выход"
        )
        try:
            choice = input("Действие: ").strip()
            if choice == "0":
                print("До свидания!")
                return
            if choice == "1":
                show_events(events, plans)
            elif choice == "2":
                show_events(search_events(events, input_nonempty("Поиск: ")),
                            plans)
            elif choice == "3":
                show_events(filter_events(
                    events, input_nonempty("Категория: ")), plans)
            elif choice == "4":
                show_events(sort_events(events), plans)
            elif choice == "5":
                handle_check(events, plans)
            elif choice == "6":
                handle_check(events, plans, save=True)
            elif choice == "7":
                handle_cancel(plans)
            elif choice == "8":
                show_plans(plans, events)
            elif choice == "9":
                stats = plan_statistics(events, plans)
                print(
                    f"Мероприятий: {stats['events']}; "
                    f"записей: {stats['plans']}; "
                    f"сумма билетов: {stats['total_price']:.2f} руб."
                )
            else:
                print("Неизвестная команда.")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота завершена.")
            return


if __name__ == "__main__":
    main()
