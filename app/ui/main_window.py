import sqlite3
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox, QAbstractItemView, QLineEdit, QLabel,
)
from app.auth import AuthService
from app.db.interface import NumberingRepository
from app.models import Employee, ROLE_LABELS
from app.phone import parse_phone
from app.ui.dialogs import (
    RegionDialog, OperatorDialog, RangeDialog, EmployeeDialog, PasswordDialog,
)


class TablePage(QWidget):
    """Страница: панель кнопок + таблица."""

    def __init__(self, headers: list[str]):
        super().__init__()
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.buttons = QHBoxLayout()
        layout = QVBoxLayout(self)
        layout.addLayout(self.buttons)
        layout.addWidget(self.table)

    def add_button(self, text: str, handler) -> None:
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        self.buttons.addWidget(btn)

    def fill(self, rows: list[list]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem("" if value is None else str(value)))

    def selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())


class MainWindow(QMainWindow):
    def __init__(self, repo: NumberingRepository, user: Employee, auth: AuthService):
        super().__init__()
        self.repo = repo
        self.user = user
        self.auth = auth
        self.is_admin = user.role == "admin"
        self.setWindowTitle(f"Россвязь: план нумерации — {user.full_name} ({ROLE_LABELS[user.role]})")
        self.resize(950, 540)

        # вкладка «Поиск по номеру»
        self.search_page = QWidget()
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+7 903 123-45-67")
        self.phone_input.returnPressed.connect(self.search_number)
        find_btn = QPushButton("Определить")
        find_btn.clicked.connect(self.search_number)
        self.result = QLabel("Введите номер и нажмите «Определить».")
        self.result.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.phone_input)
        row.addWidget(find_btn)
        lay = QVBoxLayout(self.search_page)
        lay.addLayout(row)
        lay.addWidget(self.result)
        lay.addStretch()

        self.ranges = TablePage(["ID", "DEF", "От", "До", "Ёмкость", "Оператор", "Регион", "Внёс"])
        self.ranges.add_button("Добавить диапазон", self.add_range)
        self.ranges.add_button("Удалить диапазон", self.delete_range)
        self.operators = TablePage(["ID", "Оператор", "ИНН"])
        self.operators.add_button("Добавить оператора", self.add_operator)
        self.regions = TablePage(["ID", "Код", "Регион"])
        self.regions.add_button("Добавить регион", self.add_region)

        tabs = QTabWidget()
        tabs.addTab(self.search_page, "Поиск по номеру")
        tabs.addTab(self.ranges, "Диапазоны")
        tabs.addTab(self.operators, "Операторы")
        tabs.addTab(self.regions, "Регионы")

        # вкладка «Работники» доступна только администратору
        self.employees = None
        if self.is_admin:
            self.employees = TablePage(["ID", "ФИО", "Должность", "Логин", "Роль", "Статус"])
            self.employees.add_button("Добавить работника", self.add_employee)
            self.employees.add_button("Сбросить пароль", self.reset_password)
            self.employees.add_button("Отключить / включить", self.toggle_employee)
            tabs.addTab(self.employees, "Работники")

        # у каждого работника свой пароль, сменить его может каждый
        pwd_btn = QPushButton("Сменить пароль")
        pwd_btn.clicked.connect(self.change_own_password)
        tabs.setCornerWidget(pwd_btn)

        self.setCentralWidget(tabs)
        self.refresh()

    # --- вспомогательное ---
    def _lookups(self):
        ops = {o.id: o.name for o in self.repo.list_operators()}
        regs = {r.id: f"{r.code} {r.name}" for r in self.repo.list_regions()}
        return ops, regs

    def refresh(self):
        ops, regs = self._lookups()
        staff = self.repo.list_employees()
        names = {e.id: e.full_name for e in staff}
        self.regions.fill([[r.id, r.code, r.name] for r in self.repo.list_regions()])
        self.operators.fill([[o.id, o.name, o.inn] for o in self.repo.list_operators()])
        self.ranges.fill([[r.id, r.def_code, r.range_from, r.range_to, r.capacity,
                           ops.get(r.operator_id), regs.get(r.region_id), names.get(r.created_by)]
                          for r in self.repo.list_ranges()])
        if self.employees is not None:
            self.employees.fill([[e.id, e.full_name, e.position, e.username,
                                  ROLE_LABELS.get(e.role, e.role),
                                  "Активен" if e.is_active else "Отключён"] for e in staff])

    def _error(self, text: str):
        QMessageBox.warning(self, "Ошибка", text)

    def _run(self, action) -> bool:
        try:
            action()
        except ValueError as e:
            self._error(str(e))
            return False
        except sqlite3.IntegrityError:
            self._error("Такая запись уже существует или связана с другими данными.")
            return False
        self.refresh()
        return True

    # --- поиск ---
    def search_number(self):
        try:
            def_code, number = parse_phone(self.phone_input.text())
        except ValueError as e:
            self.result.setText(str(e))
            return
        found = self.repo.find_range(def_code, number)
        if found is None:
            self.result.setText(f"Номер +7 {def_code} {number}: диапазон не найден в базе.")
            return
        ops, regs = self._lookups()
        self.result.setText(
            f"Номер +7 {def_code} {number}\n"
            f"Оператор: {ops.get(found.operator_id)}\n"
            f"Регион: {regs.get(found.region_id)}\n"
            f"Диапазон: {found.def_code} {found.range_from}–{found.range_to}")

    # --- справочники ---
    def add_region(self):
        dlg = RegionDialog(self)
        if dlg.exec():
            self._run(lambda: self.repo.add_region(dlg.get_region()))

    def add_operator(self):
        dlg = OperatorDialog(self)
        if dlg.exec():
            self._run(lambda: self.repo.add_operator(dlg.get_operator()))

    def add_range(self):
        operators, regions = self.repo.list_operators(), self.repo.list_regions()
        if not operators or not regions:
            return self._error("Сначала добавьте хотя бы одного оператора и один регион.")
        dlg = RangeDialog(operators, regions, self)
        if dlg.exec():
            number_range = dlg.get_range()
            number_range.created_by = self.user.id      # запоминаем, кто внёс диапазон
            self._run(lambda: self.repo.add_range(number_range))

    def delete_range(self):
        if not self.is_admin:
            return self._error("Удалять диапазоны может только администратор.")
        range_id = self.ranges.selected_id()
        if range_id is None:
            return self._error("Выберите диапазон.")
        self._run(lambda: self.repo.delete_range(range_id))

    # --- работники и пароли ---
    def add_employee(self):
        dlg = EmployeeDialog(self)
        if dlg.exec():
            values = dlg.values()
            self._run(lambda: self.auth.add_employee(**values))

    def reset_password(self):
        employee_id = self.employees.selected_id()
        if employee_id is None:
            return self._error("Выберите работника.")
        dlg = PasswordDialog(ask_old=False, title="Новый пароль работника", parent=self)
        if dlg.exec():
            new = dlg.new_password()
            if self._run(lambda: self.auth.reset_password(employee_id, new)):
                QMessageBox.information(self, "Готово", "Пароль изменён.")

    def toggle_employee(self):
        employee_id = self.employees.selected_id()
        if employee_id is None:
            return self._error("Выберите работника.")
        if employee_id == self.user.id:
            return self._error("Нельзя отключить самого себя.")
        current = next(e for e in self.repo.list_employees() if e.id == employee_id)
        self._run(lambda: self.auth.set_active(employee_id, not current.is_active))

    def change_own_password(self):
        dlg = PasswordDialog(ask_old=True, title="Смена пароля", parent=self)
        if dlg.exec():
            old, new = dlg.old_password(), dlg.new_password()
            if self._run(lambda: self.auth.change_password(self.user, old, new)):
                QMessageBox.information(self, "Готово", "Пароль изменён.")
