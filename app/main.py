import sys
from PyQt6.QtWidgets import QApplication
from app.auth import AuthService
from app.db.sqlite_repo import SqliteNumberingRepository
from app.seed import seed_demo
from app.ui.dialogs import LoginDialog
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    repo = SqliteNumberingRepository("rossvyaz.db")
    seed_demo(repo)
    auth = AuthService(repo)
    auth.ensure_default_admin()
    login = LoginDialog(auth)
    if not login.exec():          # закрыли окно входа или нажали «Выход»
        sys.exit(0)
    window = MainWindow(repo, login.user, auth)   # окно знает только интерфейс репозитория
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
