"""Админ-панель приложения «Посетители» (ПР10)."""

from django.contrib import admin
from django.db.models import Count

from planner.admin import UserPlanInline
from visitors.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Список посетителей и их записи на мероприятия."""

    list_display = ("name", "age", "preferred_category", "budget",
                    "plans_total")
    list_filter = ("preferred_category",)
    search_fields = ("name", "preferred_category")
    ordering = ("name",)
    list_per_page = 20
    inlines = (UserPlanInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            plans_count=Count("plans"),
        )

    @admin.display(description="Всего записей", ordering="plans_count")
    def plans_total(self, obj):
        return obj.plans_count
