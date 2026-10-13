import sqlite3
from pathlib import Path
from app.db.interface import NumberingRepository
from app.models import Region, Operator, NumberRange, Employee


def _is_digits(value: str, length: int) -> bool:
    return len(value) == length and value.isascii() and value.isdigit()


class SqliteNumberingRepository(NumberingRepository):
    def __init__(self, path: str = "rossvyaz.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self._migrate()

    def _migrate(self) -> None:
        """Старые базы (до появления работников): добавляем колонку created_by."""
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(number_ranges)")]
        if "created_by" not in cols:
            self.conn.execute(
                "ALTER TABLE number_ranges ADD COLUMN created_by INTEGER REFERENCES employees(id)")
            self.conn.commit()

    def _insert(self, sql: str, params: tuple) -> int:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid

    # regions
    def add_region(self, region):
        return self._insert("INSERT INTO regions(code, name) VALUES (?, ?)",
                            (region.code, region.name))

    def list_regions(self):
        rows = self.conn.execute("SELECT id, code, name FROM regions ORDER BY code")
        return [Region(r["id"], r["code"], r["name"]) for r in rows]

    # operators
    def add_operator(self, operator):
        return self._insert("INSERT INTO operators(name, inn) VALUES (?, ?)",
                            (operator.name, operator.inn))

    def list_operators(self):
        rows = self.conn.execute("SELECT id, name, inn FROM operators ORDER BY name")
        return [Operator(r["id"], r["name"], r["inn"]) for r in rows]

    # number ranges
    def _validate_range(self, nr: NumberRange) -> None:
        if not _is_digits(nr.def_code, 3):
            raise ValueError("DEF-код должен состоять из 3 цифр.")
        if not (_is_digits(nr.range_from, 7) and _is_digits(nr.range_to, 7)):
            raise ValueError("Начало и конец диапазона должны состоять из 7 цифр.")
        if nr.range_from > nr.range_to:
            raise ValueError("Начало диапазона больше его конца.")
        overlap = self.conn.execute(
            "SELECT 1 FROM number_ranges WHERE def_code = ? AND range_from <= ? AND range_to >= ?",
            (nr.def_code, nr.range_to, nr.range_from)).fetchone()
        if overlap:
            raise ValueError("Диапазон пересекается с уже существующим.")

    @staticmethod
    def _to_range(r) -> NumberRange:
        return NumberRange(r["id"], r["def_code"], r["range_from"], r["range_to"],
                           r["operator_id"], r["region_id"], r["created_by"])

    def add_range(self, number_range):
        self._validate_range(number_range)
        return self._insert(
            "INSERT INTO number_ranges(def_code, range_from, range_to, operator_id, region_id, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (number_range.def_code, number_range.range_from, number_range.range_to,
             number_range.operator_id, number_range.region_id, number_range.created_by))

    def list_ranges(self):
        rows = self.conn.execute("SELECT * FROM number_ranges ORDER BY def_code, range_from")
        return [self._to_range(r) for r in rows]

    def delete_range(self, range_id):
        self.conn.execute("DELETE FROM number_ranges WHERE id = ?", (range_id,))
        self.conn.commit()

    def find_range(self, def_code, number):
        r = self.conn.execute(
            "SELECT * FROM number_ranges WHERE def_code = ? AND range_from <= ? AND range_to >= ?",
            (def_code, number, number)).fetchone()
        return self._to_range(r) if r else None

    # employees
    @staticmethod
    def _to_employee(r) -> Employee:
        return Employee(r["id"], r["full_name"], r["position"], r["username"],
                        r["password_hash"], r["salt"], r["role"], bool(r["is_active"]))

    def add_employee(self, employee):
        return self._insert(
            "INSERT INTO employees(full_name, position, username, password_hash, salt, role, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (employee.full_name, employee.position, employee.username, employee.password_hash,
             employee.salt, employee.role, int(employee.is_active)))

    def list_employees(self):
        rows = self.conn.execute("SELECT * FROM employees ORDER BY full_name")
        return [self._to_employee(r) for r in rows]

    def get_employee_by_username(self, username):
        r = self.conn.execute("SELECT * FROM employees WHERE username = ?", (username,)).fetchone()
        return self._to_employee(r) if r else None

    def update_employee_password(self, employee_id, password_hash, salt):
        self.conn.execute("UPDATE employees SET password_hash = ?, salt = ? WHERE id = ?",
                          (password_hash, salt, employee_id))
        self.conn.commit()

    def set_employee_active(self, employee_id, active):
        self.conn.execute("UPDATE employees SET is_active = ? WHERE id = ?",
                          (int(active), employee_id))
        self.conn.commit()
