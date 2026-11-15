"""Формы приложения «Каталог мероприятий» (ПР11)."""

import math
import re
from datetime import date
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Event
from homepage.forms import BootstrapFormMixin

CATEGORY_PATTERN = re.compile(r"^[a-zа-яё\- ]+$", re.IGNORECASE)
MAX_PRICE = Decimal("1000000")


def validate_category(value):
    """Категория – одно-два слова из букв, пробелов и дефисов."""
    if not CATEGORY_PATTERN.match(value.strip()):
        raise ValidationError(
            "Категория может содержать только буквы, пробел и дефис.",
            code="category",
        )


class EventForm(BootstrapFormMixin, forms.ModelForm):
    """Создание и изменение мероприятия, загрузка постера."""

    class Meta:
        model = Event
        fields = ["name", "category", "event_date", "age_limit",
                  "ticket_price", "capacity", "poster"]
        widgets = {
            "event_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
            "name": forms.TextInput(
                attrs={"placeholder": "Например: Вечер романсов"},
            ),
            "poster": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].validators.append(validate_category)

    def clean_event_date(self):
        """Новое мероприятие нельзя назначить на прошедшую дату."""
        event_date = self.cleaned_data["event_date"]
        changed = self.instance.pk is None or "event_date" in self.changed_data
        if changed and event_date < timezone.localdate():
            raise ValidationError("Дата мероприятия уже прошла.",
                                  code="past_date")
        return event_date


class EventSearchForm(BootstrapFormMixin, forms.Form):
    """Поиск мероприятий по периоду дат и предельной цене (GET)."""

    date_from = forms.DateField(
        required=False,
        label="Дата с",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={
            "invalid": "Дата «с»: введите дату в формате ГГГГ-ММ-ДД.",
        },
    )
    date_to = forms.DateField(
        required=False,
        label="Дата по",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={
            "invalid": "Дата «по»: введите дату в формате ГГГГ-ММ-ДД.",
        },
    )
    max_price = forms.CharField(
        required=False,
        label="Цена билета до, руб.",
        help_text="Можно с запятой: 1500,50",
    )

    def clean_max_price(self):
        """Принять цену с запятой или точкой; пусто – без ограничения."""
        raw = self.cleaned_data["max_price"].strip().replace(",", ".")
        if not raw:
            return MAX_PRICE
        try:
            price = float(raw)
        except ValueError:
            price = -1.0
        if not math.isfinite(price) or price < 0:
            raise ValidationError("Цена: введите неотрицательное число.")
        return Decimal(str(price))

    def clean(self):
        """Период: дата «с» не позже даты «по»."""
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from") or date.today()
        date_to = cleaned_data.get("date_to") or date.max
        if date_from > date_to:
            raise ValidationError("Дата «с» не может быть позже даты «по».")
        cleaned_data["date_from"] = date_from
        cleaned_data["date_to"] = date_to
        return cleaned_data
