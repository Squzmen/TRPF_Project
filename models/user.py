"""Посетитель культурных мероприятий."""

import math

from .event import Event


class User:
    """Пользователь с предпочтительной категорией и бюджетом."""

    def __init__(self, user_id: int, name: str, age: int,
                 preferred_category: str, budget: float) -> None:
        """Сохранить данные посетителя после проверки."""
        if (type(user_id) is not int or user_id <= 0 or
                not isinstance(name, str) or not name.strip() or
                type(age) is not int or age < 0 or
                not isinstance(preferred_category, str) or
                not preferred_category.strip() or
                type(budget) not in (int, float) or
                not math.isfinite(budget) or budget < 0):
            raise ValueError("Имя, возраст, категория или бюджет неверны.")
        self.id = user_id
        self.name = name.strip()
        self.age = age
        self.preferred_category = preferred_category.strip()
        self.budget = float(budget)

    @classmethod
    def from_data(cls, data: dict) -> "User":
        """Создать пользователя из данных JSON."""
        return cls(data["id"], data["name"], data["age"],
                   data["preferred_category"], data["budget"])

    def to_data(self) -> dict:
        """Подготовить поля пользователя для JSON."""
        return {
            "id": self.id, "name": self.name, "age": self.age,
            "preferred_category": self.preferred_category,
            "budget": self.budget,
        }

    def is_interested_in(self, event: Event) -> bool:
        """Проверить, соответствует ли мероприятие предпочтениям."""
        return self.preferred_category.casefold() == event.category.casefold()

    def __str__(self) -> str:
        """Показать имя и ID посетителя."""
        return f"{self.id}. {self.name} ({self.age} лет)"
