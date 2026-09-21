"""Связь пользователя и выбранного культурного мероприятия."""

from .event import Event
from .user import User


class Plan:
    """Запись с историей отмены; ссылки ведут на Event и User."""

    def __init__(self, plan_id: int, event: Event, user: User,
                 is_cancelled: bool = False) -> None:
        """Создать запись и сохранить связи с объектами."""
        if (type(plan_id) is not int or plan_id <= 0 or
                not isinstance(event, Event) or
                not isinstance(user, User) or
                type(is_cancelled) is not bool):
            raise ValueError("Некорректные данные записи.")
        self.id = plan_id
        self.event = event
        self.user = user
        self.is_cancelled = is_cancelled

    def cancel(self) -> None:
        """Отменить запись без удаления сведений о ней."""
        if self.is_cancelled:
            raise ValueError("Запись уже отменена.")
        self.is_cancelled = True

    def to_data(self) -> dict:
        """Сохранить в JSON только ID связей, а не вложенные объекты."""
        return {
            "id": self.id, "event_id": self.event.id,
            "user_id": self.user.id, "is_cancelled": self.is_cancelled,
        }

    def __str__(self) -> str:
        """Показать связанную запись и её состояние."""
        state = "отменена" if self.is_cancelled else "активна"
        return (f"{self.id}. {self.user.name} — {self.event.name} "
                f"({self.event.event_date.isoformat()}) [{state}]")
