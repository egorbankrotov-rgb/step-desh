from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox,
)
from app.auth import AuthService
from app.models import Region, Operator, NumberRange, Employee, ROLE_LABELS


class _BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.form = QFormLayout(self)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def finish(self):
        self.form.addRow(self.buttons)


def _password_field() -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


class RegionDialog(_BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Новый регион", parent)
        self.code = QLineEdit()
        self.code.setMaxLength(3)
        self.name = QLineEdit()
        self.form.addRow("Код субъекта:", self.code)
        self.form.addRow("Название:", self.name)
        self.finish()

    def get_region(self) -> Region:
        return Region(None, self.code.text().strip(), self.name.text().strip())


class OperatorDialog(_BaseDialog):
    def __init__(self, parent=None):
        super().__init__("Новый оператор", parent)
        self.name = QLineEdit()
        self.inn = QLineEdit()
        self.inn.setMaxLength(12)
        self.form.addRow("Название:", self.name)
        self.form.addRow("ИНН:", self.inn)
        self.finish()

    def get_operator(self) -> Operator:
        return Operator(None, self.name.text().strip(), self.inn.text().strip() or None)


class RangeDialog(_BaseDialog):
    def __init__(self, operators: list[Operator], regions: list[Region], parent=None):
        super().__init__("Новый диапазон", parent)
        self.def_code = QLineEdit()
        self.def_code.setMaxLength(3)
        self.def_code.setPlaceholderText("903")
        self.range_from = QLineEdit()
        self.range_from.setMaxLength(7)
        self.range_from.setPlaceholderText("0000000")
        self.range_to = QLineEdit()
        self.range_to.setMaxLength(7)
        self.range_to.setPlaceholderText("9999999")
        self.operator = QComboBox()
        for o in operators:
            self.operator.addItem(o.name, o.id)
        self.region = QComboBox()
        for r in regions:
            self.region.addItem(f"{r.code} — {r.name}", r.id)
        self.form.addRow("DEF-код (3 цифры):", self.def_code)
        self.form.addRow("От (7 цифр):", self.range_from)
        self.form.addRow("До (7 цифр):", self.range_to)
        self.form.addRow("Оператор:", self.operator)
        self.form.addRow("Регион:", self.region)
        self.finish()

    def get_range(self) -> NumberRange:
        return NumberRange(None, self.def_code.text().strip(), self.range_from.text().strip(),
                           self.range_to.text().strip(),
                           self.operator.currentData(), self.region.currentData())


class EmployeeDialog(_BaseDialog):
    """Новый работник со своим логином и паролем (открывает администратор)."""

    def __init__(self, parent=None):
        super().__init__("Новый работник", parent)
        self.full_name = QLineEdit()
        self.position = QLineEdit()
        self.username = QLineEdit()
        self.password = _password_field()
        self.role = QComboBox()
        for key in ("operator", "admin"):
            self.role.addItem(ROLE_LABELS[key], key)
        self.form.addRow("ФИО:", self.full_name)
        self.form.addRow("Должность:", self.position)
        self.form.addRow("Логин:", self.username)
        self.form.addRow("Пароль:", self.password)
        self.form.addRow("Роль:", self.role)
        self.finish()

    def values(self) -> dict:
        return dict(full_name=self.full_name.text(), position=self.position.text(),
                    username=self.username.text(), password=self.password.text(),
                    role=self.role.currentData())


class PasswordDialog(_BaseDialog):
    """Смена своего пароля (ask_old=True) или задание нового пароля работнику (ask_old=False)."""

    def __init__(self, ask_old: bool, title: str = "Смена пароля", parent=None):
        super().__init__(title, parent)
        self.old = _password_field() if ask_old else None
        self.new = _password_field()
        self.repeat = _password_field()
        if self.old is not None:
            self.form.addRow("Текущий пароль:", self.old)
        self.form.addRow("Новый пароль:", self.new)
        self.form.addRow("Повторите пароль:", self.repeat)
        self.finish()

    def accept(self):
        if self.new.text() != self.repeat.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return
        super().accept()

    def old_password(self) -> str:
        return self.old.text() if self.old is not None else ""

    def new_password(self) -> str:
        return self.new.text()


class LoginDialog(_BaseDialog):
    def __init__(self, auth: AuthService, parent=None):
        super().__init__("Вход для работников", parent)
        self.auth = auth
        self.user: Employee | None = None
        self.username = QLineEdit()
        self.password = _password_field()
        self.form.addRow("Логин:", self.username)
        self.form.addRow("Пароль:", self.password)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Войти")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Выход")
        self.finish()

    def accept(self):
        user = self.auth.login(self.username.text(), self.password.text())
        if user is None:
            QMessageBox.warning(self, "Ошибка",
                                "Неверный логин или пароль, либо доступ закрыт.\n"
                                "Учётные записи выдаёт администратор.")
            self.password.clear()
            return
        self.user = user
        super().accept()
