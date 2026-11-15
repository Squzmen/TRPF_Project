"""Модель посетителя (ПР9: таблица users описана классом Django ORM).

Это посетитель предметной области, а не встроенный пользователь
django.contrib.auth: регистрация и вход в систему он не обеспечивает.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class User(models.Model):
    """Посетитель, который записывается на мероприятия."""

    name = models.CharField(
        max_length=100,
        verbose_name="Имя",
    )
    age = models.PositiveSmallIntegerField(
        verbose_name="Возраст",
    )
    preferred_category = models.CharField(
        max_length=50,
        verbose_name="Любимая категория",
    )
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Бюджет, руб.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Посетитель"
        verbose_name_plural = "Посетители"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Категории хранятся строчными буквами, как и в базе ПР7.
        self.preferred_category = self.preferred_category.strip().lower()
        super().save(*args, **kwargs)

    def is_interested_in(self, event):
        """Совпадает ли категория мероприятия с любимой (правило ПР1)."""
        return self.preferred_category.casefold() == event.category.casefold()
