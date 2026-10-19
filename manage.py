#!/usr/bin/env python
"""Служебная утилита Django для управления проектом."""

import os
import sys


def main():
    """Выполнить административную команду Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leisure.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Установите зависимости "
            "(pip install -r requirements.txt) и активируйте "
            "виртуальное окружение."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
