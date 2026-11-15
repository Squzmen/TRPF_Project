"""Поиск без учёта регистра для кириллицы в SQLite.

Встроенные LIKE, lower() и upper() SQLite меняют регистр только у
латинских букв, поэтому icontains/iexact не находили «Гамлет» по запросу
«гамлет». При открытии соединения функции заменяются Python-версиями,
которые работают с Unicode. На другие СУБД это не влияет.
"""

import re
from functools import lru_cache

from django.db.backends.signals import connection_created


@lru_cache(maxsize=256)
def _like_regex(pattern, escape):
    """Перевести шаблон LIKE (% и _) в регулярное выражение."""
    parts = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if escape and char == escape and index + 1 < len(pattern):
            parts.append(re.escape(pattern[index + 1]))
            index += 2
            continue
        if char == "%":
            parts.append(".*")
        elif char == "_":
            parts.append(".")
        else:
            parts.append(re.escape(char))
        index += 1
    return re.compile("".join(parts), re.IGNORECASE | re.DOTALL)


def unicode_like(pattern, value, escape=None):
    """Аналог LIKE, сравнивающий строки без учёта регистра."""
    if pattern is None or value is None:
        return None
    return _like_regex(pattern, escape).fullmatch(str(value)) is not None


def _lower(value):
    return value.lower() if isinstance(value, str) else value


def _upper(value):
    return value.upper() if isinstance(value, str) else value


def register_functions(sender, connection, **kwargs):
    """Подключить функции к каждому новому соединению SQLite."""
    if connection.vendor != "sqlite":
        return
    raw = connection.connection
    raw.create_function("like", 2, unicode_like, deterministic=True)
    raw.create_function("like", 3, unicode_like, deterministic=True)
    raw.create_function("lower", 1, _lower, deterministic=True)
    raw.create_function("upper", 1, _upper, deterministic=True)


def connect():
    connection_created.connect(register_functions)
