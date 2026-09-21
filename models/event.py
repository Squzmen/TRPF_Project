"""Объект культурного мероприятия."""

import math
from datetime import date


class Event:
    """Мероприятие со стоимостью, возрастным порогом и вместимостью."""

    def __init__(self, event_id: int, name: str, category: str,
                 event_date: date, age_limit: int, ticket_price: float,
                 capacity: int) -> None:
        """Создать мероприятие и проверить корректность его атрибутов."""
        if (type(event_id) is not int or event_id <= 0 or
                not isinstance(name, str) or not name.strip() or
                not isinstance(category, str) or not category.strip() or
                not isinstance(event_date, date) or
                type(age_limit) is not int or age_limit < 0 or
                type(ticket_price) not in (int, float) or
                not math.isfinite(ticket_price) or ticket_price < 0 or
                not self.valid_capacity(capacity)):
            raise ValueError("Некорректные данные мероприятия.")
        self.id = event_id
        self.name = name.strip()
        self.category = category.strip()
        self.event_date = event_date
        self.age_limit = age_limit
        self.ticket_price = float(ticket_price)
        self.capacity = capacity

    @staticmethod
    def valid_capacity(capacity: int) -> bool:
        """Проверить, что вместимость неотрицательная и целая."""
        return type(capacity) is int and capacity >= 0

    @classmethod
    def from_data(cls, data: dict) -> "Event":
        """Восстановить мероприятие из записи JSON."""
        return cls(data["id"], data["name"], data["category"],
                   date.fromisoformat(data["event_date"]),
                   data["age_limit"], data["ticket_price"],
                   data["capacity"])

    def to_data(self) -> dict:
        """Подготовить примитивные поля для JSON."""
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "event_date": self.event_date.isoformat(),
            "age_limit": self.age_limit, "ticket_price": self.ticket_price,
            "capacity": self.capacity,
        }

    def is_age_allowed(self, age: int) -> bool:
        """Проверить возрастное ограничение этого мероприятия."""
        return age >= self.age_limit

    def is_budget_enough(self, budget: float) -> bool:
        """Проверить возможность купить билет на мероприятие."""
        return budget >= self.ticket_price

    def __str__(self) -> str:
        """Показать мероприятие в каталоге."""
        return (f"{self.id}. {self.name} | {self.category} | "
                f"{self.event_date.isoformat()} | "
                f"{self.ticket_price:.2f} руб.")
