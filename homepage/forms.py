"""Общие средства для форм проекта (ПР11)."""

from django import forms


class BootstrapFormMixin:
    """Добавить виджетам классы Bootstrap и подсветку полей с ошибками."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            else:
                css = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()

    def full_clean(self):
        # Проверка выполняется только при обращении к is_valid()/errors,
        # после этого поля с ошибками получают класс is-invalid.
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs["class"] += " is-invalid"
