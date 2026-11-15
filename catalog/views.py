"""Страницы каталога мероприятий.

ПР9: данные получаются средствами Django ORM (модели Event, User, Plan)
вместо SQL-запросов через sqlite3 из ПР7.
ПР10: менеджеры Event.objects.with_seats() и Plan.objects.active(),
карточка мероприятия открывается по slug.
ПР11: поиск через EventSearchForm, создание и изменение мероприятия
через EventForm с загрузкой постера (request.FILES).
"""

from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from catalog.forms import EventForm, EventSearchForm
from catalog.models import Event
from events import get_event_date_status
from planner.models import Plan
from visitors.models import User

# Разрешённые значения параметра sort и соответствующие поля order_by().
EVENT_SORT_FIELDS = {
    "date": ("event_date", "name"),
    "price": ("ticket_price", "name"),
    "-price": ("-ticket_price", "name"),
    "name": ("name",),
}


def event_list(request):
    """Страница /events/: фильтр по категории, поиск и сортировка."""
    category = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "date")
    if sort not in EVENT_SORT_FIELDS:
        sort = "date"

    events = Event.objects.with_seats()
    if category:
        events = events.filter(category__iexact=category)
    if query:
        # Поиск по нескольким полям: название или категория.
        events = events.filter(
            Q(name__icontains=query) | Q(category__icontains=query)
        )
    events = events.order_by(*EVENT_SORT_FIELDS[sort])

    categories = (
        Event.objects
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "catalog/event_list.html",
        {
            "events": events,
            "categories": categories,
            "category": category,
            "query": query,
            "sort": sort,
        },
    )


def event_search(request):
    """Страница /events/search/: поиск по периоду дат и цене билета."""
    submitted = bool(request.GET)
    # Форма связывается с GET-данными только после отправки.
    form = EventSearchForm(request.GET if submitted else None)

    events = []
    if submitted and form.is_valid():
        data = form.cleaned_data
        # Несколько условий в одном filter() объединяются через AND.
        events = Event.objects.with_seats().filter(
            event_date__range=(data["date_from"], data["date_to"]),
            ticket_price__lte=data["max_price"],
        ).order_by("event_date", "name")

    return render(
        request,
        "catalog/event_search.html",
        {
            "form": form,
            "events": events,
            "submitted": submitted,
        },
    )


def event_recommend(request):
    """Страница /events/recommend/: подбор мероприятий для посетителя."""
    raw_user = request.GET.get("user", "").strip()

    users = User.objects.order_by("name")
    selected = None
    events = []
    error = None
    if raw_user:
        if raw_user.isdigit():
            selected = User.objects.filter(pk=int(raw_user)).first()
        if selected is None:
            error = "Посетитель с таким номером не найден."
        else:
            # Мероприятия, на которые посетитель уже записан (активно).
            booked = Plan.objects.active().filter(
                user=selected,
            ).values_list("event_id", flat=True)
            events = (
                Event.objects.with_seats()
                .filter(
                    category__iexact=selected.preferred_category,
                    age_limit__lte=selected.age,
                    ticket_price__lte=selected.budget,
                    seats_left__gt=0,
                )
                .upcoming(date.today())
                .exclude(pk__in=booked)
                .order_by("event_date", "name")
            )

    return render(
        request,
        "catalog/event_recommend.html",
        {
            "users": users,
            "selected": selected,
            "events": events,
            "error": error,
            "raw_user": raw_user,
        },
    )


def event_redirect(request, event_id):
    """Старый адрес /events/<id>/ перенаправляет на адрес по slug."""
    event = get_object_or_404(Event, pk=event_id)
    return redirect(event, permanent=True)


def event_detail(request, slug):
    """Страница /events/<slug>/; если мероприятия нет – ответ 404."""
    event = get_object_or_404(Event.objects.with_seats(), slug=slug)
    # Обратная связь related_name="plans": активные записи мероприятия.
    plans = event.plans.active().select_related("user")

    return render(
        request,
        "catalog/event_detail.html",
        {
            "event": event,
            "seats_left": event.seats_left,
            "date_status": get_event_date_status(
                event.event_date,
                date.today(),
            ),
            "plans": plans,
        },
    )


def event_create(request):
    """Страница /events/create/: новое мероприятие с постером."""
    if request.method == "POST":
        # Файлы формы передаются отдельно – через request.FILES.
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save()
            messages.success(request, f"Мероприятие «{event}» добавлено.")
            return redirect(event)
    else:
        form = EventForm()
    return render(
        request,
        "catalog/event_form.html",
        {"form": form, "title": "Новое мероприятие"},
    )


def event_update(request, slug):
    """Страница /events/<slug>/edit/: изменение мероприятия и постера."""
    event = get_object_or_404(Event, slug=slug)
    form = EventForm(
        request.POST or None,
        request.FILES or None,
        instance=event,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Изменения сохранены.")
        return redirect(event)
    return render(
        request,
        "catalog/event_form.html",
        {"form": form, "title": f"Изменение: {event.name}", "event": event},
    )
