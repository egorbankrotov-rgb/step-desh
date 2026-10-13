import pytest
from app.auth import AuthService


def _auth_with(repo, *names):
    auth = AuthService(repo)
    for name in names:
        auth.add_employee(f"Работник {name}", "Инженер", name, "secret1")
    return auth


def test_add_employee_and_login(repo):
    auth = _auth_with(repo, "anna")
    emp = auth.login("anna", "secret1")
    assert emp.username == "anna" and emp.full_name == "Работник anna" and emp.role == "operator"


def test_wrong_password_rejected(repo):
    auth = _auth_with(repo, "anna")
    assert auth.login("anna", "wrong") is None
    assert auth.login("nobody", "secret1") is None


def test_each_employee_has_separate_password(repo):
    auth = AuthService(repo)
    auth.add_employee("Анна", "Инженер", "anna", "samepass")
    auth.add_employee("Борис", "Инженер", "boris", "samepass")
    a, b = repo.get_employee_by_username("anna"), repo.get_employee_by_username("boris")
    assert a.salt != b.salt and a.password_hash != b.password_hash   # даже при одинаковом пароле
    auth.reset_password(a.id, "newpass1")
    assert auth.login("anna", "newpass1") is not None
    assert auth.login("anna", "samepass") is None
    assert auth.login("boris", "samepass") is not None               # пароль Бориса не затронут


def test_duplicate_username_rejected(repo):
    auth = _auth_with(repo, "anna")
    with pytest.raises(ValueError):
        auth.add_employee("Другая Анна", "Инженер", "anna", "other123")


def test_short_password_and_empty_fields_rejected(repo):
    auth = AuthService(repo)
    with pytest.raises(ValueError):
        auth.add_employee("Анна", "Инженер", "anna", "123")
    with pytest.raises(ValueError):
        auth.add_employee("", "Инженер", "anna", "secret1")
    with pytest.raises(ValueError):
        auth.add_employee("Анна", "Инженер", "  ", "secret1")
    with pytest.raises(ValueError):
        auth.add_employee("Анна", "Инженер", "anna", "secret1", role="boss")


def test_password_is_not_stored_in_plain_text(repo):
    _auth_with(repo, "anna")
    emp = repo.get_employee_by_username("anna")
    assert "secret1" not in (emp.password_hash + emp.salt)


def test_default_admin_created_once(repo):
    auth = AuthService(repo)
    auth.ensure_default_admin()
    auth.ensure_default_admin()
    assert auth.login("admin", "admin").role == "admin"
    assert len(repo.list_employees()) == 1


def test_change_own_password(repo):
    auth = _auth_with(repo, "anna")
    emp = auth.login("anna", "secret1")
    auth.change_password(emp, "secret1", "newpass1")
    assert auth.login("anna", "secret1") is None
    assert auth.login("anna", "newpass1") is not None
    auth.change_password(emp, "newpass1", "third123")        # повторная смена тем же объектом
    assert auth.login("anna", "third123") is not None


def test_change_password_wrong_old_or_short_new(repo):
    auth = _auth_with(repo, "anna")
    emp = auth.login("anna", "secret1")
    with pytest.raises(ValueError):
        auth.change_password(emp, "wrong", "newpass1")
    with pytest.raises(ValueError):
        auth.change_password(emp, "secret1", "1")
    assert auth.login("anna", "secret1") is not None


def test_deactivated_employee_cannot_login(repo):
    auth = _auth_with(repo, "anna")
    emp = repo.get_employee_by_username("anna")
    auth.set_active(emp.id, False)
    assert auth.login("anna", "secret1") is None
    auth.set_active(emp.id, True)
    assert auth.login("anna", "secret1") is not None


def test_cannot_deactivate_last_admin(repo):
    auth = AuthService(repo)
    auth.ensure_default_admin()
    admin = repo.get_employee_by_username("admin")
    with pytest.raises(ValueError):
        auth.set_active(admin.id, False)
    auth.add_employee("Второй админ", "Руководитель", "boss", "secret1", role="admin")
    auth.set_active(admin.id, False)                          # теперь можно
    assert auth.login("admin", "admin") is None
