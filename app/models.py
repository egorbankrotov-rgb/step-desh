from dataclasses import dataclass

ROLE_LABELS = {"admin": "Администратор", "operator": "Оператор"}


@dataclass
class Region:
    id: int | None
    code: str            # код субъекта РФ, например "77"
    name: str


@dataclass
class Operator:
    id: int | None
    name: str
    inn: str | None = None


@dataclass
class Employee:
    """Работник Россвязи. У каждого свой логин и свой пароль (хранится только хэш)."""
    id: int | None
    full_name: str
    position: str
    username: str
    password_hash: str
    salt: str
    role: str = "operator"      # "admin" или "operator"
    is_active: bool = True      # отключённый работник войти не может


@dataclass
class NumberRange:
    """Диапазон номеров: DEF-код (3 цифры) + номера от..до (7 цифр)."""
    id: int | None
    def_code: str
    range_from: str
    range_to: str
    operator_id: int
    region_id: int
    created_by: int | None = None     # employees.id: кто внёс диапазон

    @property
    def capacity(self) -> int:
        return int(self.range_to) - int(self.range_from) + 1
