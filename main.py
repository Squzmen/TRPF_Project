"""Начальный сценарий системы планирования культурного досуга."""

from datetime import date


EVENT_NAME = "Спектакль «Гамлет»"
EVENT_CATEGORY = "театр"
EVENT_DATE = date(2026, 10, 17)
EVENT_AGE_LIMIT = 12
EVENT_TICKET_PRICE = 1500.0
EVENT_HAS_AVAILABLE_SEATS = True


def is_age_allowed(user_age: int, age_limit: int) -> bool:
    """Проверить, соответствует ли возраст пользователя ограничению."""
    if user_age >= age_limit:
        return True
    return False


def is_category_suitable(preferred_category: str, event_category: str) -> bool:
    """Проверить соответствие мероприятия предпочтительной категории."""
    normalized_preference = preferred_category.strip().lower()
    normalized_category = event_category.strip().lower()
    if normalized_preference == normalized_category:
        return True
    return False


def is_budget_enough(user_budget: float, ticket_price: float) -> bool:
    """Проверить, достаточно ли бюджета для покупки билета."""
    if user_budget >= ticket_price:
        return True
    return False


def get_event_date_status(event_date: date, current_date: date) -> str:
    """Определить временной статус мероприятия."""
    if event_date < current_date:
        return "Мероприятие уже прошло"
    if event_date == current_date:
        return "Мероприятие проходит сегодня"
    return "Мероприятие еще впереди"


def get_recommendation(
    age_allowed: bool,
    category_suitable: bool,
    budget_enough: bool,
    date_available: bool,
    has_available_seats: bool,
) -> str:
    """Сформировать итоговую рекомендацию для пользователя."""
    if not has_available_seats:
        return "Мероприятие не подходит: свободных мест нет."
    if not date_available:
        return "Мероприятие не подходит: оно уже прошло."
    if not age_allowed:
        return "Мероприятие не подходит: не пройдено возрастное ограничение."
    if not category_suitable:
        return "Мероприятие не подходит по выбранной категории."
    if not budget_enough:
        return "Мероприятие не подходит: стоимость билета превышает бюджет."
    return "Мероприятие подходит. Его можно добавить в план досуга."


def main() -> None:
    """Запустить диалог проверки мероприятия для пользователя."""
    print("Система планирования культурного досуга")
    print("Проверим, подходит ли вам выбранное мероприятие.\n")

    user_name = input("Введите имя: ").strip()
    user_age = int(input("Введите возраст: "))
    preferred_category = input("Введите интересующую категорию: ")
    user_budget = float(input("Введите доступный бюджет в рублях: "))

    age_allowed = is_age_allowed(user_age, EVENT_AGE_LIMIT)
    category_suitable = is_category_suitable(
        preferred_category,
        EVENT_CATEGORY,
    )
    budget_enough = is_budget_enough(user_budget, EVENT_TICKET_PRICE)
    current_date = date.today()
    date_status = get_event_date_status(EVENT_DATE, current_date)
    date_available = EVENT_DATE >= current_date
    recommendation = get_recommendation(
        age_allowed,
        category_suitable,
        budget_enough,
        date_available,
        EVENT_HAS_AVAILABLE_SEATS,
    )

    print(f"\nПользователь: {user_name}")
    print(f"Мероприятие: {EVENT_NAME}")
    print(f"Категория: {EVENT_CATEGORY}")
    print(f"Дата: {EVENT_DATE.strftime('%d.%m.%Y')}")
    print(f"Стоимость билета: {EVENT_TICKET_PRICE:.2f} руб.")
    print(f"Статус даты: {date_status}")
    print(f"Результат: {recommendation}")


if __name__ == "__main__":
    main()

