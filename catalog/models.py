"""Модель мероприятия каталога.

ПР9: таблица events описана моделью Django ORM.
ПР10: менеджер EventQuerySet, вычисляемое поле is_family (GeneratedField),
адрес страницы по slug и get_absolute_url().
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Case, Count, F, Q, Value, When
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode

# Мероприятие считается семейным, если на него пускают детей с 6 лет.
FAMILY_AGE_LIMIT = 6


def make_slug(name, queryset, exclude_pk=None):
    """Транслитерировать название и сделать slug уникальным (-2, -3…)."""
    base = slugify(unidecode(name))[:200] or "event"
    others = queryset.exclude(pk=exclude_pk) if exclude_pk else queryset
    slug = base
    number = 2
    while others.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class EventQuerySet(models.QuerySet):
    """Запросы к мероприятиям, общие для нескольких страниц."""

    def with_seats(self):
        """Добавить число активных записей и свободных мест."""
        from planner.models import Plan

        return self.annotate(
            active_plans=Count(
                "plans",
                filter=Q(plans__status=Plan.Status.ACTIVE),
            ),
        ).annotate(
            seats_left=F("capacity") - F("active_plans"),
        )

    def upcoming(self, today):
        """Мероприятия, которые ещё не прошли."""
        return self.filter(event_date__gte=today)


class EventManager(models.Manager.from_queryset(EventQuerySet)):
    """Менеджер Event.objects с методами EventQuerySet."""


class Event(models.Model):
    """Культурное мероприятие с датой, ценой билета и числом мест."""

    name = models.CharField(
        max_length=200,
        verbose_name="Название",
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        verbose_name="Адрес страницы (slug)",
        help_text="Формируется автоматически из названия латиницей.",
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
    is_family = models.GeneratedField(
        expression=Case(
            When(age_limit__lte=FAMILY_AGE_LIMIT, then=Value(True)),
            default=Value(False),
            output_field=models.BooleanField(),
        ),
        output_field=models.BooleanField(),
        db_persist=True,
        verbose_name="Семейное (6+ и младше)",
    )
    ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Цена билета, руб.",
    )
    capacity = models.PositiveIntegerField(
        verbose_name="Вместимость",
        help_text="Максимальное число посетителей, которые могут записаться.",
    )

    objects = EventManager()

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
        if not self.slug:
            self.slug = make_slug(self.name, Event.objects, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Адрес карточки мероприятия по именованному маршруту."""
        return reverse("catalog:detail", kwargs={"slug": self.slug})

    def is_age_allowed(self, age):
        """Проходит ли посетитель возрастное ограничение (правило ПР1)."""
        return age >= self.age_limit

    def is_budget_enough(self, budget):
        """Хватает ли бюджета на билет (правило ПР1)."""
        return budget >= self.ticket_price
