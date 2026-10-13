import sqlite3
import pytest
from app.db.interface import NumberingRepository
from app.db.sqlite_repo import SqliteNumberingRepository
from app.models import Region, Operator, NumberRange, Employee


def _setup(repo):
    region_id = repo.add_region(Region(None, "77", "Москва"))
    operator_id = repo.add_operator(Operator(None, "Оператор А"))
    return operator_id, region_id


def _range(op, reg, a="0000000", b="4999999", code="903"):
    return NumberRange(None, code, a, b, op, reg)


def test_repo_implements_interface(repo):
    assert isinstance(repo, NumberingRepository)


def test_add_and_list_regions_and_operators(repo):
    _setup(repo)
    assert [r.name for r in repo.list_regions()] == ["Москва"]
    assert [o.name for o in repo.list_operators()] == ["Оператор А"]


def test_duplicate_region_code_rejected(repo):
    repo.add_region(Region(None, "77", "Москва"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_region(Region(None, "77", "Другой"))


def test_add_range_and_capacity(repo):
    op, reg = _setup(repo)
    repo.add_range(_range(op, reg, "0000000", "0999999"))
    ranges = repo.list_ranges()
    assert len(ranges) == 1
    assert ranges[0].capacity == 1_000_000


def test_range_requires_existing_operator(repo):
    _, reg = _setup(repo)
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_range(_range(999, reg))


def test_reversed_range_rejected(repo):
    op, reg = _setup(repo)
    with pytest.raises(ValueError):
        repo.add_range(_range(op, reg, "5000000", "1000000"))


def test_bad_def_code_rejected(repo):
    op, reg = _setup(repo)
    with pytest.raises(ValueError):
        repo.add_range(_range(op, reg, code="90"))


def test_overlapping_range_rejected_but_adjacent_allowed(repo):
    op, reg = _setup(repo)
    repo.add_range(_range(op, reg, "0000000", "4999999"))
    with pytest.raises(ValueError):
        repo.add_range(_range(op, reg, "4000000", "6999999"))
    repo.add_range(_range(op, reg, "5000000", "9999999"))   # соседний диапазон можно
    repo.add_range(_range(op, reg, "0000000", "4999999", code="904"))  # другой DEF можно
    assert len(repo.list_ranges()) == 3


def test_find_range_hit_and_miss(repo):
    op, reg = _setup(repo)
    repo.add_range(_range(op, reg, "1000000", "1999999"))
    hit = repo.find_range("903", "1500000")
    assert hit is not None and hit.operator_id == op and hit.region_id == reg
    assert repo.find_range("903", "2500000") is None
    assert repo.find_range("999", "1500000") is None


def test_delete_range(repo):
    op, reg = _setup(repo)
    rid = repo.add_range(_range(op, reg))
    repo.delete_range(rid)
    assert repo.list_ranges() == []


def _employee(username="ivanov", full_name="Иванов Иван"):
    return Employee(None, full_name, "Инженер", username, "hash", "00ff", "operator", True)


def test_range_records_who_created_it(repo):
    op, reg = _setup(repo)
    emp_id = repo.add_employee(_employee())
    nr = _range(op, reg)
    nr.created_by = emp_id
    repo.add_range(nr)
    assert repo.list_ranges()[0].created_by == emp_id


def test_range_with_unknown_employee_rejected(repo):
    op, reg = _setup(repo)
    nr = _range(op, reg)
    nr.created_by = 999
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_range(nr)


def test_add_and_find_employee(repo):
    repo.add_employee(_employee("ivanov"))
    repo.add_employee(_employee("petrov", "Петров Пётр"))
    assert [e.username for e in repo.list_employees()] == ["ivanov", "petrov"]
    assert repo.get_employee_by_username("petrov").full_name == "Петров Пётр"
    assert repo.get_employee_by_username("nobody") is None


def test_duplicate_username_rejected_by_db(repo):
    repo.add_employee(_employee("ivanov"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_employee(_employee("ivanov", "Другой"))


def test_cannot_delete_employee_referenced_by_range(repo):
    op, reg = _setup(repo)
    emp_id = repo.add_employee(_employee())
    nr = _range(op, reg)
    nr.created_by = emp_id
    repo.add_range(nr)
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))


def test_migrates_old_database_without_created_by():
    import os, tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "old.db")
        old = sqlite3.connect(path)
        old.executescript("""
            CREATE TABLE regions (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL);
            CREATE TABLE operators (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, inn TEXT);
            CREATE TABLE number_ranges (
                id INTEGER PRIMARY KEY AUTOINCREMENT, def_code TEXT NOT NULL, range_from TEXT NOT NULL,
                range_to TEXT NOT NULL, operator_id INTEGER NOT NULL, region_id INTEGER NOT NULL);
            INSERT INTO regions(code, name) VALUES ('77', 'Москва');
            INSERT INTO operators(name) VALUES ('Старый оператор');
            INSERT INTO number_ranges(def_code, range_from, range_to, operator_id, region_id)
                VALUES ('903', '0000000', '9999999', 1, 1);
        """)
        old.commit()
        old.close()
        repo = SqliteNumberingRepository(path)
        ranges = repo.list_ranges()
        repo.conn.close()
    assert len(ranges) == 1 and ranges[0].created_by is None
