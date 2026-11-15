"""Админ-панель приложения «Планы посетителей» (ПР10)."""

from django.contrib import admin

from planner.models import Plan


class PlanInlineBase(admin.TabularInline):
    """Записи внутри карточки мероприятия или посетителя."""

    model = Plan
    extra = 0
    show_change_link = True
    readonly_fields = ("created_at",)


class EventPlanInline(PlanInlineBase):
    """Записи на мероприятие: выбирается посетитель."""

    fields = ("user", "status", "comment", "created_at")
    autocomplete_fields = ("user",)


class UserPlanInline(PlanInlineBase):
    """Записи посетителя: выбирается мероприятие."""

    fields = ("event", "status", "comment", "created_at")
    autocomplete_fields = ("event",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Список записей: статус, связанные объекты, массовые действия."""

    list_display = (
        "id",
        "event",
        "event_date",
        "user",
        "status",
        "created_at",
    )
    list_display_links = ("id", "event")
    list_editable = ("status",)
    list_filter = ("status", "event__category", "event")
    search_fields = ("event__name", "user__name")
    ordering = ("event__event_date", "id")
    list_per_page = 20
    # Мероприятие и посетитель загружаются в том же SQL-запросе (JOIN).
    list_select_related = ("event", "user")
    autocomplete_fields = ("event", "user")
    readonly_fields = ("created_at",)
    date_hierarchy = "event__event_date"
    actions = ("cancel_plans", "restore_plans", "complete_plans")

    @admin.display(description="Дата мероприятия",
                   ordering="event__event_date")
    def event_date(self, obj):
        return obj.event.event_date

    def _set_status(self, request, queryset, status, message):
        updated = queryset.update(status=status)
        self.message_user(request, f"{message}: {updated}.")

    @admin.action(description="Отменить выбранные записи")
    def cancel_plans(self, request, queryset):
        self._set_status(request, queryset, Plan.Status.CANCELLED,
                         "Отменено записей")

    @admin.action(description="Вернуть выбранные записи в активные")
    def restore_plans(self, request, queryset):
        self._set_status(request, queryset, Plan.Status.ACTIVE,
                         "Возвращено в активные")

    @admin.action(description="Отметить как посещённые")
    def complete_plans(self, request, queryset):
        self._set_status(request, queryset, Plan.Status.COMPLETED,
                         "Отмечено посещённых")
