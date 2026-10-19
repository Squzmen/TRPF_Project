-- ==========================================================
-- Система планирования культурного досуга: структура базы данных
-- СУБД: SQLite. Выполняется командой python -m db.import_json
-- (или функцией db.database.create_schema).
-- ==========================================================

-- Мероприятия (класс Event)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    event_date TEXT NOT NULL,                  -- дата в формате ГГГГ-ММ-ДД
    age_limit INTEGER NOT NULL DEFAULT 0 CHECK (age_limit >= 0),
    ticket_price REAL NOT NULL CHECK (ticket_price >= 0),
    capacity INTEGER NOT NULL CHECK (capacity >= 0)
);

-- Посетители (класс User)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    preferred_category TEXT NOT NULL,
    budget REAL NOT NULL CHECK (budget >= 0)
);

-- Записи посетителей на мероприятия (класс Plan)
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_cancelled INTEGER NOT NULL DEFAULT 0
        CHECK (is_cancelled IN (0, 1)),        -- 0 - активна, 1 - отменена
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Индексы по внешним ключам ускоряют соединения и подсчёты
CREATE INDEX IF NOT EXISTS idx_plans_event_id ON plans(event_id);
CREATE INDEX IF NOT EXISTS idx_plans_user_id ON plans(user_id);
