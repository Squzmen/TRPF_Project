# Система планирования культурного досуга

Проект ПР1 → ПР2 → ПР3 → ПР5 → ПР6 → ПР7 → ПР9: подбор культурных
мероприятий и сохранение записей посетителей. Консольное приложение (ПР3)
дополнено веб-интерфейсом на Django (ПР5), страницы которого в ПР6 переведены
на шаблоны Django, в ПР7 получили базу SQLite и SQL-запросы, а в ПР9 слой
доступа к данным переведён на Django ORM: модели, связи, миграции и
ORM-запросы. Исходные проверки возраста, категории, бюджета, даты и свободных
мест сохранены и по-прежнему работают в консольной версии.

## Назначение

Приложение помогает посетителю выбрать мероприятие по категории, дате,
стоимости билета и возрастному ограничению и записаться на него.

**Консольная версия** (`python main.py`): просмотр, поиск по названию,
фильтрация по категории и сортировка по цене; проверка пригодности
мероприятия для посетителя; добавление и отмена записи; история записей,
посетители и статистика; добавление посетителя и нового мероприятия.

**Веб-интерфейс** (ПР5–ПР9): список мероприятий с поиском, фильтром по
категории и сортировкой; карточка мероприятия с числом свободных мест и
записавшимися посетителями; поиск по датам и цене; подбор мероприятий для
посетителя; список записей с фильтрацией по дате, мероприятию, посетителю и
статусу, сортировкой и постраничным выводом; карточка записи; статистика.
Изменение данных через веб-формы будет реализовано после изучения форм Django.

## Используемые технологии

* Python 3.10+;
* Django 5.2 — веб-фреймворк, Django ORM — доступ к данным;
* Django Template Language — шаблоны страниц;
* HTML5, CSS3, JavaScript — разметка, собственные стили и скрипт;
* Bootstrap 5.3 — базовое оформление;
* SQLite — база данных (`db.sqlite3` для Django, `data/culture.sqlite` — исходная база ПР7);
* JSON — исходные данные и хранилище консольной версии;
* pytest, pytest-django — автоматизированные тесты; flake8 — проверка качества кода.

## Объектная модель консольной версии

| Класс | Данные | Основное поведение |
| --- | --- | --- |
| `Event` | `id`, `name`, `category`, `event_date`, `age_limit`, `ticket_price`, `capacity` | проверка возраста, цены и вместимости, `__str__` |
| `User` | `id`, `name`, `age`, `preferred_category`, `budget` | проверка интереса, `from_data`, `__str__` |
| `Plan` | `id`, ссылки на `Event` и `User`, `is_cancelled` | `cancel`, сериализация, `__str__` |

Классы пакета `models/` используются только консольной версией; веб-часть
работает с моделями Django (раздел «Модели Django ORM»).

## Веб-интерфейс

Django-проект называется `leisure`, веб-часть разделена на приложения по
сущностям предметной области:

| Приложение | Назначение | Модель |
| --- | --- | --- |
| `homepage` | главная страница, страница ошибки 404, общие статические файлы | — |
| `catalog` | каталог мероприятий | `Event` |
| `visitors` | посетители (ПР9) | `User` |
| `planner` | записи посетителей на мероприятия | `Plan` |

Приложения названы `catalog` и `planner`, а не `events` и `plans`: пакеты с
такими именами скрыли бы модули `events.py` и `plans.py` консольной версии.
Модель `visitors.User` — посетитель предметной области, а не встроенный
пользователь `django.contrib.auth`.

### Страницы и маршруты

| URL | Имя маршрута | View-функция | Данные |
| --- | --- | --- | --- |
| `/` | `homepage:index` | `homepage.views.index` | — |
| `/events/` (`?q=&category=&sort=`) | `catalog:list` | `catalog.views.event_list` | ORM |
| `/events/search/` | `catalog:search` | `catalog.views.event_search` | ORM |
| `/events/recommend/` | `catalog:recommend` | `catalog.views.event_recommend` | ORM |
| `/events/<int:event_id>/` | `catalog:detail` | `catalog.views.event_detail` | ORM |
| `/plans/` (`?date=&event=&user=&status=&sort=&page=`) | `planner:list` | `planner.views.plan_list` | ORM |
| `/plans/statistics/` | `planner:statistics` | `planner.views.statistics` | ORM |
| `/plans/<int:plan_id>/` | `planner:detail` | `planner.views.plan_detail` | ORM |

Пространства имён задаются переменной `app_name` в `urls.py` приложений.
Карточки мероприятия и записи получают объект через `get_object_or_404()`:
при отсутствии объекта возвращается ответ 404. Любой неизвестный адрес
обрабатывает `handler404` (`homepage.views.page_not_found`, шаблон
`homepage/404.html`); собственная страница видна при `DEBUG = False`.

### Шаблоны Django

* `templates/base.html` — базовый шаблон: кодировка, Bootstrap, собственный
  CSS, логотип, навигация, подвал, JavaScript; блоки `title` и `content`;
* `templates/includes/navigation.html` — навигация со ссылками `{% url %}`;
* `templates/includes/pagination.html` — навигация по страницам: `page_obj`,
  `has_previous`, `has_next`, ссылки `{% querystring page=... %}`
  сохраняют параметры фильтрации и сортировки;
* `catalog/includes/event_card.html` — карточка мероприятия;
  `planner/includes/plan_status.html` — статус записи;
* фильтры шаблонов: `length`, `default`, `date`, `floatformat`, `linebreaksbr`.

### Статические файлы

Каталог `homepage/static/homepage/`: `css/style.css`, `js/main.js` и
`img/logo.png`. Подключаются тегами `{% load static %}` и `{% static %}`.

## Модели Django ORM (ПР9)

| Модель | Приложение | Поля | Связи |
| --- | --- | --- | --- |
| `Event` — мероприятие | `catalog` | `name`, `category`, `event_date` (DateField), `age_limit`, `ticket_price` (DecimalField, ≥ 0), `capacity` | обратная связь `event.plans` |
| `User` — посетитель | `visitors` | `name`, `age`, `preferred_category`, `budget` | обратная связь `user.plans` |
| `Plan` — запись | `planner` | `event`, `user`, `is_cancelled`, `comment`, `created_at` | `ForeignKey` на `Event` и `User` |

* первичные ключи `id` (BigAutoField) создаёт Django;
* `Plan.event` и `Plan.user` — `ForeignKey(on_delete=models.PROTECT,
  related_name="plans")`: мероприятие или посетителя с записями удалить
  нельзя, история записей сохраняется; столбцы `event_id` и `user_id`
  создаются автоматически;
* `Meta`: сортировка по умолчанию, `verbose_name`, ограничение
  `CheckConstraint` на неотрицательную цену билета;
* методы моделей: `Event.is_age_allowed()`, `Event.is_budget_enough()`,
  `User.is_interested_in()`, `Plan.cancel()`; категории при сохранении
  приводятся к строчным буквам.

### Миграции

Файлы `catalog/migrations/0001_initial.py`,
`visitors/migrations/0001_initial.py`, `planner/migrations/0001_initial.py`
хранятся в репозитории. Порядок работы:

```powershell
python manage.py makemigrations        # создать миграции по изменениям моделей
python manage.py showmigrations        # состояние миграций ([X] — применена)
python manage.py sqlmigrate planner 0001   # SQL миграции
python manage.py migrate               # применить к db.sqlite3
```

### Перенос данных из базы ПР7

Выбран вариант «таблицы, управляемые Django, и перенос данных»: исходная
база `data/culture.sqlite` не изменяется и служит источником, Django работает
с `db.sqlite3`.

```powershell
python -m db.inspect_source_db      # таблицы, столбцы, число записей, проверка ссылок
python manage.py migrate
python -m db.import_sqlite_to_orm   # перенос с сохранением id и связей
```

Скрипт `db/import_sqlite_to_orm.py` переносит сначала мероприятия и
посетителей, затем записи (`update_or_create(pk=...)` в
`transaction.atomic()`), преобразует даты в `date`, цены в `Decimal`,
`is_cancelled` в `bool`. Повторный запуск не создаёт дублей. Ожидаемый
результат: 5 мероприятий, 7 посетителей, 6 записей.

### ORM-запросы проекта

| Направление | Где используется | ORM-выражение |
| --- | --- | --- |
| получение набора | все списки | `Event.objects.all()`, `User.objects.order_by("name")` |
| отдельный объект | карточки | `get_object_or_404(Plan.objects.select_related("event", "user"), pk=...)` |
| фильтрация по одному условию | `/events/?category=` | `filter(category__iexact=category)` |
| несколько условий | `/events/search/`, `/events/recommend/` | `filter(event_date__range=..., ticket_price__lte=...)` |
| поле связанной модели | `/plans/?date=` | `filter(event__event_date=selected_date)` |
| исключение | `/events/recommend/` | `exclude(pk__in=booked)` |
| поиск по строке и нескольким полям | `/events/?q=` | `filter(Q(name__icontains=q) \| Q(category__icontains=q))` |
| сортировка | `/events/?sort=`, `/plans/?sort=` | `order_by(*EVENT_SORT_FIELDS[sort])`, `order_by("event__name", "id")` |
| связанные данные | `/plans/` | `annotate(event_name=F("event__name"), user_name=F("user__name")).values(...)` |
| сокращённый набор полей | `/events/recommend/`, `/events/` | `values_list("event_id", flat=True)`, `values_list("category", flat=True).distinct()` |
| агрегирование | статистика | `aggregate(Count("id"), Sum(...), Avg(...), Min(...), Max(...))` |
| аннотирование и группировка | статистика, списки | `annotate(active_plans=Count("plans", filter=Q(...)))`, `values("category").annotate(...)` |
| условие на агрегат (HAVING) | статистика | `annotate(...).filter(active_plans__gte=2)` |
| постраничный вывод | `/plans/` | `Paginator(plans, 5).get_page(request.GET.get("page"))` |

Пользовательские параметры проверяются: сортировка выбирается только из
словарей `EVENT_SORT_FIELDS` и `PLAN_SORT_FIELDS`, идентификаторы — через
`isdigit()`, даты — `date.fromisoformat()` с сообщением об ошибке, номер
страницы — `get_page()` (некорректное значение даёт первую страницу).
Отменённые записи не учитываются в свободных местах, подборе и статистике;
статистика строится от `Event` и `User`, поэтому объекты без записей
остаются в результате со значением 0.

Поиск без учёта регистра по кириллице: встроенные `LIKE`/`lower()` SQLite
работают только с латиницей, поэтому `catalog/sqlite_functions.py` при
открытии соединения подключает Unicode-версии этих функций
(`icontains`, `iexact` находят «Гамлет» по запросу «гамлет»).

### Слой SQL ПР7

Файлы `sql/schema.sql`, `sql/queries.sql`, `db/database.py`,
`db/import_json.py` и `data/culture.sqlite` сохранены как предыдущая
реализация и источник данных переноса; представления их больше не
используют. Обновить исходную базу из JSON можно командой
`python -m db.import_json`.

## Файлы и данные

```text
TRPF_Project/
├── manage.py            # управление Django-проектом
├── leisure/             # настройки проекта (settings.py, urls.py, wsgi.py, asgi.py)
├── templates/           # base.html, includes/navigation.html, includes/pagination.html
├── homepage/            # приложение: главная, 404, статические файлы
├── catalog/             # приложение: модель Event, представления, шаблоны мероприятий
│   └── migrations/
├── visitors/            # приложение: модель User (посетитель)
│   └── migrations/
├── planner/             # приложение: модель Plan, список, карточка, статистика
│   └── migrations/
├── db/                  # import_sqlite_to_orm.py, inspect_source_db.py (ПР9); database.py, import_json.py (ПР7)
├── sql/                 # schema.sql, queries.sql (ПР7)
├── main.py              # консольное меню (ПР3)
├── models/              # классы Event, User и Plan консольной версии
├── events.py            # поиск, фильтрация, сортировка и проверки ПР1
├── plans.py             # доступность, создание, отмена и статистика
├── storage.py           # загрузка и сохранение объектов в JSON
├── utils.py             # безопасный ввод
├── data/                # events.json, users.json, plans.json, culture.sqlite (ПР7)
├── tests/               # проверки pytest (консоль, SQL-слой, модели, веб)
└── requirements.txt     # Django, pytest, pytest-django, flake8
```

В репозитории лежат демонстрационные данные: пять мероприятий, семь
посетителей и шесть записей (одна из них отменена). База Django `db.sqlite3`
в репозиторий не входит: после клонирования она создаётся миграциями и
заполняется скриптом переноса.

## Запуск и проверка

В каталоге `TRPF_Project` (PowerShell):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python -m db.import_sqlite_to_orm
python manage.py check
python manage.py runserver
```

После запуска откройте `http://127.0.0.1:8000/`. Консольная версия запускается
командой `python main.py`. Проверка кода:

```powershell
python manage.py makemigrations --check
python manage.py showmigrations
pytest -v
flake8 . --extend-exclude=venv
```

## Текущее состояние

На ПР9 веб-интерфейс переведён на Django ORM:

* описаны модели `Event`, `User`, `Plan` и связи «многие к одному»;
* созданы и применены миграции, данные перенесены из базы ПР7 без потери
  идентификаторов и связей;
* представления получают данные через ORM (не менее 15 различных
  ORM-выражений: фильтрация, `exclude()`, поиск `icontains`, `Q`, сортировка,
  `select_related()`, `values()`, `aggregate()`, `annotate()`, `Paginator`);
* список записей поддерживает фильтрацию, сортировку и пагинацию с
  сохранением параметров;
* консольная версия по-прежнему работает с JSON.

Отложено до следующих работ: административная панель, формы, создание и
отмена записей через веб.

## Автор

Пшеничнов Александр Андреевич, группа ЭФБО-11-24.
