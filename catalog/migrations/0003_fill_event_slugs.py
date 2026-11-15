"""Миграция данных ПР10: slug для уже существующих мероприятий.

Поле slug добавлено миграцией 0002 без ограничения уникальности; здесь
каждое мероприятие получает транслитерированный уникальный slug, после
чего миграция 0004 делает поле уникальным.
"""

from django.db import migrations
from django.utils.text import slugify
from unidecode import unidecode


def fill_slugs(apps, schema_editor):
    Event = apps.get_model("catalog", "Event")
    used = set()
    for event in Event.objects.order_by("pk"):
        base = slugify(unidecode(event.name))[:200] or "event"
        slug = base
        number = 2
        while slug in used:
            slug = f"{base}-{number}"
            number += 1
        used.add(slug)
        event.slug = slug
        event.save(update_fields=["slug"])


def clear_slugs(apps, schema_editor):
    apps.get_model("catalog", "Event").objects.update(slug="")


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_event_slug_is_family_help_text"),
    ]

    operations = [
        migrations.RunPython(fill_slugs, clear_slugs),
    ]
