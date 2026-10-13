import pytest
from app.db.sqlite_repo import SqliteNumberingRepository


@pytest.fixture
def repo():
    return SqliteNumberingRepository(":memory:")   # чистая БД для каждого теста
