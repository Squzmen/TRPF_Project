"""Миграция данных ПР10: перенос is_cancelled в поле status.

Выполняется до удаления is_cancelled (миграция 0004): иначе сведения
об отменённых записях были бы потеряны.
"""

from django.db import migrations


def migrate_plan_statuses(apps, schema_editor):
    # Историческая модель: состояние на момент этой миграции.
    Plan = apps.get_model("planner", "Plan")
    Plan.objects.filter(is_cancelled=True).update(status="cancelled")
    Plan.objects.filter(is_cancelled=False).update(status="active")


def reverse_plan_statuses(apps, schema_editor):
    # Откат: восстанавливаем булево поле по статусу.
    Plan = apps.get_model("planner", "Plan")
    Plan.objects.filter(status="cancelled").update(is_cancelled=True)
    Plan.objects.exclude(status="cancelled").update(is_cancelled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0002_plan_status"),
    ]

    operations = [
        migrations.RunPython(
            migrate_plan_statuses,
            reverse_plan_statuses,
        ),
    ]
