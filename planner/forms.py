"""Формы приложения «Планы посетителей» (ПР11).

PlanFilterForm – обычная форма (forms.Form) для GET-фильтров списка.
PlanForm – форма на основе модели (ModelForm) для создания и
редактирования записи; проверяет правила предметной области ПР1.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Event
from events import get_recommendation
from homepage.forms import BootstrapFormMixin
from planner.models import Plan
from planner.validators import validate_no_links
from visitors.models import User

SORT_CHOICES = [
    ("date", "По дате"),
    ("event", "По мероприятию"),
    ("user", "По посетителю"),
]


class PlanFilterForm(BootstrapFormMixin, forms.Form):
    """Фильтры списка записей; имена полей совпадают с GET-параметрами."""

    date = forms.DateField(
        required=False,
        label="Дата мероприятия",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"invalid": "Укажите дату в формате ГГГГ-ММ-ДД."},
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.order_by("event_date", "name"),
        required=False,
        label="Мероприятие",
        empty_label="Все мероприятия",
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.order_by("name"),
        required=False,
        label="Посетитель",
        empty_label="Все посетители",
    )
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[("", "Все записи"), *Plan.Status.choices],
    )
    sort = forms.ChoiceField(
        required=False,
        label="Сортировка",
        choices=SORT_CHOICES,
    )


class PlanForm(BootstrapFormMixin, forms.ModelForm):
    """Создание и редактирование записи посетителя на мероприятие.

    Поле status в форму не входит: новая запись всегда активна, а отмена
    выполняется отдельной кнопкой (POST /plans/<id>/cancel/).
    """

    class Meta:
        model = Plan
        fields = ["event", "user", "comment"]
        labels = {
            "event": "Мероприятие",
            "user": "Посетитель",
            "comment": "Комментарий",
        }
        help_texts = {
            "event": "Можно выбрать только предстоящее мероприятие "
                     "со свободными местами.",
            "user": "Возраст, бюджет и любимая категория посетителя "
                    "проверяются по правилам ПР1.",
            "comment": "Необязательно, до 500 символов, без ссылок.",
        }
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Например: нужен пандус или место у прохода",
            }),
        }
        error_messages = {
            "event": {"required": "Выберите мероприятие."},
            "user": {"required": "Выберите посетителя."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event"].queryset = Event.objects.order_by(
            "event_date", "name")
        self.fields["user"].queryset = User.objects.order_by("name")
        self.fields["comment"].max_length = 500
        self.fields["comment"].validators.append(validate_no_links)

    def clean_event(self):
        """Проверка одного поля: на прошедшее мероприятие не записывают."""
        event = self.cleaned_data["event"]
        if event.event_date < timezone.localdate():
            raise ValidationError(
                "Нельзя записаться на прошедшее мероприятие.",
                code="past_event",
            )
        return event

    def clean(self):
        """Проверка взаимосвязанных полей: свободные места и правила ПР1."""
        cleaned_data = super().clean()
        event = cleaned_data.get("event")
        user = cleaned_data.get("user")
        if event is None or user is None:
            return cleaned_data

        # Активные записи, кроме редактируемой (иначе она конфликтовала
        # бы сама с собой при сохранении без изменений).
        others = Plan.objects.active().filter(event=event)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)

        if others.filter(user=user).exists():
            raise ValidationError(
                "Посетитель уже записан на это мероприятие.",
                code="duplicate",
            )

        reason = get_recommendation(
            event.is_age_allowed(user.age),
            user.is_interested_in(event),
            event.is_budget_enough(user.budget),
            event.event_date >= timezone.localdate(),
            others.count() < event.capacity,
        )
        if not reason.startswith("Мероприятие подходит"):
            raise ValidationError(reason, code="rules")
        return cleaned_data
