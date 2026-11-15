"""Модель записи посетителя на мероприятие.

ПР9: таблица plans описана моделью Django ORM.
ПР10: статус записи на TextChoices и собственный менеджер PlanQuerySet.
"""

from django.db import models

from catalog.models import Event
from visitors.models import User


class PlanQuerySet(models.QuerySet):
    """Повторно используемые условия выборки записей."""

    def active(self):
        """Только активные записи – они занимают место на мероприятии."""
        return self.filter(status=Plan.Status.ACTIVE)

    def cancelled(self):
        """Только отменённые записи."""
        return self.filter(status=Plan.Status.CANCELLED)

    def completed(self):
        """Только записи на посещённые мероприятия."""
        return self.filter(status=Plan.Status.COMPLETED)

    def for_date(self, selected_date):
        """Записи на мероприятия указанной даты (datetime.date)."""
        return self.filter(event__event_date=selected_date)

    def with_details(self):
        """Загрузить мероприятие и посетителя одним запросом (JOIN)."""
        return self.select_related("event", "user")


class PlanManager(models.Manager.from_queryset(PlanQuerySet)):
    """Менеджер Plan.objects с методами PlanQuerySet."""


class Plan(models.Model):
    """Запись посетителя на мероприятие: связь «многие к одному»."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        CANCELLED = "cancelled", "Отменена"
        COMPLETED = "completed", "Посещена"

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
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Статус записи",
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

    objects = PlanManager()

    class Meta:
        ordering = ["event__event_date", "pk"]
        verbose_name = "Запись"
        verbose_name_plural = "Записи"

    def __str__(self):
        return f"{self.user} — {self.event} ({self.event.event_date:%d.%m.%Y})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def cancel(self):
        """Отменить запись: статус меняется, запись остаётся в истории."""
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])

    def complete(self):
        """Отметить, что посетитель побывал на мероприятии."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status"])
