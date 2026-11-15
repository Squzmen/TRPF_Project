"""Админ-панель приложения «Каталог мероприятий» (ПР10)."""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from catalog.models import Event
from planner.admin import EventPlanInline
from planner.models import Plan

admin.site.site_header = "Культурный досуг — администрирование"
admin.site.site_title = "Культурный досуг"
admin.site.index_title = "Управление данными проекта"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Список мероприятий: столбцы, поиск, фильтры, записи (inline)."""

    list_display = (
        "name",
        "category",
        "event_date",
        "ticket_price",
        "capacity",
        "active_plans",
        "is_family",
    )
    list_display_links = ("name",)
    # Цена и вместимость редактируются прямо в списке.
    list_editable = ("ticket_price", "capacity")
    list_filter = ("category", "is_family", "event_date")
    search_fields = ("name", "category")
    ordering = ("event_date", "name")
    list_per_page = 20
    date_hierarchy = "event_date"
    readonly_fields = ("slug", "is_family", "poster_preview")
    fieldsets = (
        (None, {"fields": ("name", "slug", "category")}),
        ("Постер", {"fields": ("poster", "poster_preview")}),
        ("Условия посещения", {
            "fields": ("event_date", "age_limit", "is_family",
                       "ticket_price", "capacity"),
        }),
    )
    inlines = (EventPlanInline,)

    def get_queryset(self, request):
        # Число активных записей считается в том же SQL-запросе.
        return super().get_queryset(request).annotate(
            active_plans_count=Count(
                "plans",
                filter=Q(plans__status=Plan.Status.ACTIVE),
            ),
        )

    @admin.display(description="Текущий постер")
    def poster_preview(self, obj):
        if not obj.poster:
            return "Не загружен"
        return format_html('<img src="{}" style="max-height: 150px">',
                           obj.poster.url)

    @admin.display(description="Активных записей",
                   ordering="active_plans_count")
    def active_plans(self, obj):
        return obj.active_plans_count
