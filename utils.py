"""Безопасный ввод значений пользователем."""

import math
from datetime import date


def input_nonempty(prompt: str) -> str:
    """Повторять запрос, пока не получена непустая строка."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Введите непустое значение.")


def input_int(prompt: str, minimum: int = 0) -> int:
    """Повторять запрос до получения целого числа не ниже minimum."""
    while True:
        try:
            value = int(input(prompt))
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Введите целое число не меньше {minimum}.")


def input_float(prompt: str, minimum: float = 0) -> float:
    """Запросить конечное число не меньше minimum."""
    while True:
        try:
            value = float(input(prompt).replace(",", "."))
            if math.isfinite(value) and value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Введите число не меньше {minimum}.")


def input_date(prompt: str) -> date:
    """Повторять запрос до получения календарной даты ГГГГ-ММ-ДД."""
    while True:
        try:
            return date.fromisoformat(input(prompt).strip())
        except ValueError:
            print("Введите существующую дату в формате ГГГГ-ММ-ДД.")
