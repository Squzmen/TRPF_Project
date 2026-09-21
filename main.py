"""Консольный интерфейс проекта культурного досуга на объектной модели."""

from datetime import date

from events import (
    filter_events, find_event, get_event_date_status, search_events,
    sort_events,
)
from models import Event, Plan, User
from plans import (
    cancel_plan, create_plan, find_plan, plan_recommendation,
    plan_statistics, remaining_seats,
)
from storage import (
    StorageError, load_data, save_events, save_plans, save_users,
)
from utils import input_date, input_float, input_int, input_nonempty


def show_events(events: list[Event], plans: list[Plan]) -> None:
    """Показать объекты каталога и количество доступных мест."""
    if not events:
        print("Мероприятий не найдено.")
    for event in events:
        print(f"{event} | мест: {remaining_seats(plans, event)}")


def show_plans(plans: list[Plan]) -> None:
    """Показать активные и отмененные записи с сохранением истории."""
    if not plans:
        print("Планов пока нет.")
    for plan in plans:
        print(plan)


def show_users(users: list[User]) -> None:
    """Вывести зарегистрированных посетителей."""
    if not users:
        print("Посетителей пока нет.")
    for user in users:
        print(user)


def ask_event(events: list[Event]) -> Event | None:
    """Найти мероприятие по введенному ID."""
    event = find_event(events, input_int("ID мероприятия: ", minimum=1))
    if event is None:
        print("Мероприятие не найдено.")
    return event


def ask_user(users: list[User]) -> User:
    """Получить проверенные параметры посетителя как объект User."""
    name = input_nonempty("Имя: ")
    age = input_int("Возраст: ", minimum=0)
    category = input_nonempty("Интересующая категория: ")
    budget = input_float("Бюджет (руб.): ", minimum=0)
    user_id = max((user.id for user in users), default=0) + 1
    return User(user_id, name, age, category, budget)


def existing_user(users: list[User], candidate: User) -> User | None:
    """Проверить повтор имени и совпадение параметров профиля."""
    for user in users:
        if user.name.casefold() == candidate.name.casefold():
            if (user.age != candidate.age or
                    user.preferred_category.casefold() !=
                    candidate.preferred_category.casefold() or
                    user.budget != candidate.budget):
                raise ValueError(
                    "Посетитель с таким именем уже есть, но данные отличаются."
                )
            return user
    return None


def handle_check(events: list[Event], users: list[User],
                 plans: list[Plan], save: bool = False) -> None:
    """Проверить условия ПР1 и при необходимости создать запись ПР3."""
    event = ask_event(events)
    if event is None:
        return
    candidate = ask_user(users)
    date_status = get_event_date_status(event.event_date, date.today())
    print(f"Статус даты: {date_status}")
    print(plan_recommendation(plans, event, candidate))
    if not save:
        return
    try:
        user = existing_user(users, candidate)
        is_new = user is None
        user = candidate if is_new else user
        plan = create_plan(plans, event, user)
    except ValueError as error:
        print(f"Запись не создана: {error}")
        return
    if is_new:
        users.append(user)
    users_saved = False
    try:
        # Ссылки из plans.json всегда должны указывать на сохраненных users.
        save_users(users)
        users_saved = True
        save_plans(plans)
    except StorageError as error:
        plans.remove(plan)
        if is_new and not users_saved:
            users.remove(user)
        print(f"Запись не сохранена: {error}")
    else:
        print(f"Запись добавлена, ID: {plan.id}.")


def handle_cancel(users: list[User], plans: list[Plan]) -> None:
    """Отменить запись с сохранением объекта в истории."""
    plan = find_plan(plans, input_int("ID записи: ", minimum=1))
    if plan is None:
        print("Запись не найдена.")
        return
    try:
        cancel_plan(plans, plan.id)
    except ValueError as error:
        print(f"Отмена не выполнена: {error}")
        return
    try:
        save_users(users)
        save_plans(plans)
    except StorageError as error:
        plan.is_cancelled = False
        print(f"Отмена не сохранена: {error}")
    else:
        print("Запись отменена.")


def handle_add_user(users: list[User]) -> None:
    """Сохранить нового посетителя отдельно от записи на событие."""
    candidate = ask_user(users)
    try:
        if existing_user(users, candidate) is not None:
            print("Посетитель уже зарегистрирован.")
            return
    except ValueError as error:
        print(error)
        return
    users.append(candidate)
    try:
        save_users(users)
    except StorageError as error:
        users.remove(candidate)
        print(f"Посетитель не сохранен: {error}")
    else:
        print(f"Посетитель добавлен, ID: {candidate.id}.")


def handle_add_event(events: list[Event]) -> None:
    """Создать и сохранить мероприятие с пользовательской датой."""
    event_id = max((event.id for event in events), default=0) + 1
    name = input_nonempty("Название: ")
    category = input_nonempty("Категория: ")
    event_day = input_date("Дата (ГГГГ-ММ-ДД): ")
    age = input_int("Возрастное ограничение: ", minimum=0)
    price = input_float("Стоимость билета: ", minimum=0)
    capacity = input_int("Количество мест: ", minimum=0)
    event = Event(event_id, name, category, event_day, age, price, capacity)
    events.append(event)
    try:
        save_events(events)
    except StorageError as error:
        events.remove(event)
        print(f"Мероприятие не сохранено: {error}")
    else:
        print(f"Мероприятие добавлено, ID: {event.id}.")


def main() -> None:
    """Загрузить три коллекции объектов и обслуживать меню."""
    try:
        events, users, plans = load_data()
    except StorageError as error:
        print(f"Не удалось загрузить данные: {error}")
        return
    print("Система планирования культурного досуга — ПР3")
    while True:
        print(
            "\n1. Мероприятия  2. Поиск  3. Фильтр по категории\n"
            "4. Сортировка по цене  5. Проверить мероприятие\n"
            "6. Добавить в план  7. Отменить запись\n"
            "8. Показать планы  9. Статистика\n"
            "10. Добавить посетителя  11. Посетители\n"
            "12. Добавить мероприятие  0. Выход"
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
                handle_check(events, users, plans)
            elif choice == "6":
                handle_check(events, users, plans, save=True)
            elif choice == "7":
                handle_cancel(users, plans)
            elif choice == "8":
                show_plans(plans)
            elif choice == "9":
                stats = plan_statistics(events, plans)
                print(
                    f"Мероприятий: {stats['events']}; "
                    f"записей: {stats['plans']}; "
                    f"сумма билетов: {stats['total_price']:.2f} руб."
                )
            elif choice == "10":
                handle_add_user(users)
            elif choice == "11":
                show_users(users)
            elif choice == "12":
                handle_add_event(events)
            else:
                print("Неизвестная команда.")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота завершена.")
            return


if __name__ == "__main__":
    main()
