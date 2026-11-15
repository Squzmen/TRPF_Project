"""Модель записи посетителя на мероприятие (ПР9: таблица plans)."""

from django.db import models

from catalog.models import Event
from visitors.models import User


class Plan(models.Model):
    """Запись посетителя на мероприятие: связь «многие к одному»."""

    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="plans",
        verbose_name="Мероприятие",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="plans",
        verbose_name="Посетитель",
    )
    is_cancelled = models.BooleanField(
        default=False,
        verbose_name="Запись отменена",
    )
    comment = models.TextField(
        blank=True,
        default="",
        verbose_name="Комментарий",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата оформления",
    )

    class Meta:
        ordering = ["event__event_date", "pk"]
        verbose_name = "Запись"
        verbose_name_plural = "Записи"

    def __str__(self):
        return f"{self.user} — {self.event} ({self.event.event_date:%d.%m.%Y})"

    def cancel(self):
        """Отменить запись, не удаляя её из истории."""
        self.is_cancelled = True
        self.save(update_fields=["is_cancelled"])
