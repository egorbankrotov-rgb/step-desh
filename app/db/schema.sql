CREATE TABLE IF NOT EXISTS regions (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operators (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    inn  TEXT
);
CREATE TABLE IF NOT EXISTS employees (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    position      TEXT NOT NULL DEFAULT '',
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'operator' CHECK (role IN ('admin', 'operator')),
    is_active     INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS number_ranges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    def_code    TEXT NOT NULL CHECK (length(def_code) = 3 AND def_code NOT GLOB '*[^0-9]*'),
    range_from  TEXT NOT NULL CHECK (length(range_from) = 7 AND range_from NOT GLOB '*[^0-9]*'),
    range_to    TEXT NOT NULL CHECK (length(range_to) = 7 AND range_to NOT GLOB '*[^0-9]*'),
    operator_id INTEGER NOT NULL REFERENCES operators(id) ON DELETE RESTRICT,
    region_id   INTEGER NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    created_by  INTEGER REFERENCES employees(id) ON DELETE RESTRICT,
    CHECK (range_from <= range_to)
);
