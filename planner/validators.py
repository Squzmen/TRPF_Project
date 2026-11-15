"""Пользовательские валидаторы-функции (ПР11)."""

import re

from django.core.exceptions import ValidationError

LINK_PATTERN = re.compile(r"(https?://|www\.)", re.IGNORECASE)


def validate_no_links(value):
    """Комментарий к записи не должен содержать ссылок (защита от спама)."""
    if LINK_PATTERN.search(value or ""):
        raise ValidationError(
            "Комментарий не должен содержать ссылок.",
            code="links",
        )
