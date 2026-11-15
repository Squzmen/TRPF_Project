"""Модель мероприятия каталога (ПР9: таблица events описана Django ORM)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Event(models.Model):
    """Культурное мероприятие с датой, ценой билета и числом мест."""

    name = models.CharField(
        max_length=200,
        verbose_name="Название",
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Категория",
    )
    event_date = models.DateField(
        verbose_name="Дата проведения",
    )
    age_limit = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Возрастное ограничение",
    )
    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Цена билета, руб.",
    )
    capacity = models.PositiveIntegerField(
        verbose_name="Вместимость",
    )

    class Meta:
        ordering = ["event_date", "name"]
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ticket_price__gte=0),
                name="event_ticket_price_non_negative",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Сравнение категорий в запросах выполняется по строчным буквам.
        self.category = self.category.strip().lower()
        super().save(*args, **kwargs)

    def is_age_allowed(self, age):
        """Проходит ли посетитель возрастное ограничение (правило ПР1)."""
        return age >= self.age_limit

    def is_budget_enough(self, budget):
        """Хватает ли бюджета на билет (правило ПР1)."""
        return budget >= self.ticket_price
