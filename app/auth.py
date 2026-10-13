import hashlib
import hmac
import secrets

from app.db.interface import NumberingRepository
from app.models import Employee, ROLE_LABELS

ITERATIONS = 200_000
MIN_PASSWORD = 4


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Возвращает (хэш, соль) в hex. Соль у каждого работника своя, пароль в открытом виде не хранится."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD} символов.")


class AuthService:
    """Учётные записи работников: добавление, вход, смена и сброс пароля, отключение."""

    def __init__(self, repo: NumberingRepository):
        self.repo = repo

    def add_employee(self, full_name: str, position: str, username: str,
                     password: str, role: str = "operator") -> Employee:
        full_name, position, username = full_name.strip(), position.strip(), username.strip()
        if not full_name:
            raise ValueError("Введите ФИО.")
        if not username:
            raise ValueError("Введите логин.")
        if role not in ROLE_LABELS:
            raise ValueError("Неизвестная роль.")
        _check_password(password)
        if self.repo.get_employee_by_username(username):
            raise ValueError("Такой логин уже занят.")
        pwd_hash, salt = hash_password(password)
        employee = Employee(None, full_name, position, username, pwd_hash, salt, role, True)
        employee.id = self.repo.add_employee(employee)
        return employee

    def login(self, username: str, password: str) -> Employee | None:
        employee = self.repo.get_employee_by_username(username.strip())
        if employee and employee.is_active and verify_password(
                password, employee.password_hash, employee.salt):
            return employee
        return None

    def change_password(self, employee: Employee, old: str, new: str) -> None:
        """Работник меняет СВОЙ пароль, зная текущий."""
        fresh = self.repo.get_employee_by_username(employee.username)
        if fresh is None or not verify_password(old, fresh.password_hash, fresh.salt):
            raise ValueError("Неверный текущий пароль.")
        self.reset_password(fresh.id, new)

    def reset_password(self, employee_id: int, new: str) -> None:
        """Задаёт новый пароль (вызывает администратор)."""
        _check_password(new)
        pwd_hash, salt = hash_password(new)
        self.repo.update_employee_password(employee_id, pwd_hash, salt)

    def set_active(self, employee_id: int, active: bool) -> None:
        employees = self.repo.list_employees()
        target = next((e for e in employees if e.id == employee_id), None)
        if target is None:
            raise ValueError("Работник не найден.")
        if not active and target.role == "admin" and target.is_active:
            others = [e for e in employees
                      if e.id != employee_id and e.role == "admin" and e.is_active]
            if not others:
                raise ValueError("Нельзя отключить последнего администратора.")
        self.repo.set_employee_active(employee_id, active)

    def ensure_default_admin(self) -> None:
        """При первом запуске создаёт admin / admin (смените пароль!)."""
        if not self.repo.get_employee_by_username("admin"):
            self.add_employee("Администратор системы", "Администратор", "admin", "admin", "admin")
