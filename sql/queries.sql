-- ==========================================================
-- Система планирования культурного досуга: SQL-запросы проекта
-- Проверка: sqlite3 data/culture.sqlite < sql/queries.sql
-- В запросах приведены примеры значений; в веб-приложении они заменяются
-- параметрами ? (значения передаются отдельно от текста запроса).
-- ==========================================================


-- ----------------------------------------------------------
-- 1. Список всех мероприятий со свободными местами
--    (SELECT, подзапрос). Страница /events/
-- ----------------------------------------------------------
SELECT
    e.id,
    e.name,
    e.category,
    e.event_date,
    e.age_limit,
    e.ticket_price,
    e.capacity,
    e.capacity - (
        SELECT COUNT(*)
        FROM plans AS p
        WHERE p.event_id = e.id
          AND p.is_cancelled = 0
    ) AS seats_left
FROM events AS e
ORDER BY e.event_date, e.name;


-- ----------------------------------------------------------
-- 2. Список категорий мероприятий без повторов (DISTINCT)
--    Выпадающий список на странице /events/
-- ----------------------------------------------------------
SELECT DISTINCT
    category
FROM events
ORDER BY category;


-- ----------------------------------------------------------
-- 3. Список посетителей (SELECT, сортировка по имени)
--    Выпадающий список на странице /events/recommend/
-- ----------------------------------------------------------
SELECT
    id,
    name,
    age,
    preferred_category,
    budget
FROM users
ORDER BY name;


-- ----------------------------------------------------------
-- 4. Мероприятия выбранной категории (WHERE)
--    Страница /events/?category=концерт; в приложении: category = ?
-- ----------------------------------------------------------
SELECT
    e.id,
    e.name,
    e.category,
    e.event_date,
    e.age_limit,
    e.ticket_price,
    e.capacity,
    e.capacity - (
        SELECT COUNT(*)
        FROM plans AS p
        WHERE p.event_id = e.id
          AND p.is_cancelled = 0
    ) AS seats_left
FROM events AS e
WHERE e.category = 'концерт'
ORDER BY e.event_date, e.name;


-- ----------------------------------------------------------
-- 5. Поиск мероприятий по периоду дат и предельной цене билета
--    (WHERE, BETWEEN). Страница /events/search/;
--    в приложении: BETWEEN ? AND ? и ticket_price <= ?
-- ----------------------------------------------------------
SELECT
    e.id,
    e.name,
    e.category,
    e.event_date,
    e.age_limit,
    e.ticket_price,
    e.capacity,
    e.capacity - (
        SELECT COUNT(*)
        FROM plans AS p
        WHERE p.event_id = e.id
          AND p.is_cancelled = 0
    ) AS seats_left
FROM events AS e
WHERE e.event_date BETWEEN '2026-11-01' AND '2026-12-31'
  AND e.ticket_price <= 2000
ORDER BY e.event_date, e.name;


-- ----------------------------------------------------------
-- 6. Подбор мероприятий для посетителя (JOIN, WHERE, NOT IN)
--    Мероприятие должно подходить по категории, возрасту и бюджету,
--    быть не раньше выбранной даты, иметь свободные места, и посетитель
--    не должен быть на него уже записан. Страница /events/recommend/;
--    в приложении: JOIN users ON u.id = ? и event_date >= ?
-- ----------------------------------------------------------
SELECT
    e.id,
    e.name,
    e.category,
    e.event_date,
    e.age_limit,
    e.ticket_price,
    e.capacity,
    e.capacity - (
        SELECT COUNT(*)
        FROM plans AS p
        WHERE p.event_id = e.id
          AND p.is_cancelled = 0
    ) AS seats_left
FROM events AS e
JOIN users AS u
    ON u.id = 6
WHERE e.category = u.preferred_category
  AND e.age_limit <= u.age
  AND e.ticket_price <= u.budget
  AND e.event_date >= '2026-10-19'
  AND e.capacity > (
        SELECT COUNT(*)
        FROM plans AS p
        WHERE p.event_id = e.id
          AND p.is_cancelled = 0
  )
  AND e.id NOT IN (
        SELECT p.event_id
        FROM plans AS p
        WHERE p.user_id = u.id
          AND p.is_cancelled = 0
  )
ORDER BY e.event_date, e.name;


-- ----------------------------------------------------------
-- 7. Все записи с названием мероприятия и именем посетителя
--    (JOIN трёх таблиц). Страница /plans/
-- ----------------------------------------------------------
SELECT
    p.id,
    p.is_cancelled,
    e.id AS event_id,
    e.name AS event_name,
    e.category,
    e.event_date,
    e.ticket_price,
    u.id AS user_id,
    u.name AS user_name
FROM plans AS p
JOIN events AS e
    ON p.event_id = e.id
JOIN users AS u
    ON p.user_id = u.id
ORDER BY e.event_date, p.id;


-- ----------------------------------------------------------
-- 8. Только активные записи (JOIN, WHERE)
--    Страница /plans/?status=active
-- ----------------------------------------------------------
SELECT
    p.id,
    p.is_cancelled,
    e.id AS event_id,
    e.name AS event_name,
    e.category,
    e.event_date,
    e.ticket_price,
    u.id AS user_id,
    u.name AS user_name
FROM plans AS p
JOIN events AS e
    ON p.event_id = e.id
JOIN users AS u
    ON p.user_id = u.id
WHERE p.is_cancelled = 0
ORDER BY e.event_date, p.id;


-- ----------------------------------------------------------
-- 9. Общие показатели активных записей
--    (агрегатные функции COUNT, SUM, AVG, MIN, MAX).
--    Страница /plans/statistics/
-- ----------------------------------------------------------
SELECT
    COUNT(p.id) AS active_plans,
    COALESCE(SUM(e.ticket_price), 0) AS total_price,
    COALESCE(AVG(e.ticket_price), 0) AS avg_price,
    COALESCE(MIN(e.ticket_price), 0) AS min_price,
    COALESCE(MAX(e.ticket_price), 0) AS max_price
FROM plans AS p
JOIN events AS e
    ON p.event_id = e.id
WHERE p.is_cancelled = 0;


-- ----------------------------------------------------------
-- 10. Записи по каждому мероприятию (LEFT JOIN, GROUP BY, COUNT)
--     Мероприятия без записей остаются в результате со значением 0.
--     Страница /plans/statistics/
-- ----------------------------------------------------------
SELECT
    e.id,
    e.name AS event_name,
    e.category,
    e.capacity,
    COUNT(p.id) AS active_plans,
    e.capacity - COUNT(p.id) AS seats_left,
    COUNT(p.id) * e.ticket_price AS revenue
FROM events AS e
LEFT JOIN plans AS p
    ON p.event_id = e.id
   AND p.is_cancelled = 0
GROUP BY e.id, e.name, e.category, e.capacity, e.ticket_price
ORDER BY active_plans DESC, e.name;


-- ----------------------------------------------------------
-- 11. Сводка по категориям (GROUP BY, COUNT, MIN, AVG, MAX, SUM)
--     Страница /plans/statistics/
-- ----------------------------------------------------------
SELECT
    category,
    COUNT(*) AS events_count,
    MIN(ticket_price) AS min_price,
    ROUND(AVG(ticket_price), 2) AS avg_price,
    MAX(ticket_price) AS max_price,
    SUM(capacity) AS total_seats
FROM events
GROUP BY category
ORDER BY events_count DESC, category;


-- ----------------------------------------------------------
-- 12. Мероприятия, на которые записано не менее двух человек
--     (GROUP BY, HAVING). Страница /plans/statistics/
-- ----------------------------------------------------------
SELECT
    e.name AS event_name,
    COUNT(p.id) AS active_plans
FROM events AS e
JOIN plans AS p
    ON p.event_id = e.id
WHERE p.is_cancelled = 0
GROUP BY e.id, e.name
HAVING COUNT(p.id) >= 2
ORDER BY active_plans DESC, e.name;


-- ----------------------------------------------------------
-- 13. Активность посетителей: число записей и сумма билетов
--     (два LEFT JOIN, GROUP BY, COUNT, SUM).
--     Страница /plans/statistics/
-- ----------------------------------------------------------
SELECT
    u.id,
    u.name AS user_name,
    u.budget,
    COUNT(p.id) AS active_plans,
    COALESCE(SUM(e.ticket_price), 0) AS spent
FROM users AS u
LEFT JOIN plans AS p
    ON p.user_id = u.id
   AND p.is_cancelled = 0
LEFT JOIN events AS e
    ON p.event_id = e.id
GROUP BY u.id, u.name, u.budget
ORDER BY spent DESC, u.name;
