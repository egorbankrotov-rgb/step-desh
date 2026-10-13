from app.db.interface import NumberingRepository
from app.models import Region, Operator, NumberRange


def seed_demo(repo: NumberingRepository) -> None:
    """Вымышленные демо-данные для первого запуска (не реальный реестр)."""
    if repo.list_operators():
        return
    reg = {c: repo.add_region(Region(None, c, n)) for c, n in [
        ("77", "Москва"), ("78", "Санкт-Петербург"),
        ("16", "Республика Татарстан"), ("50", "Московская область")]}
    op = {n: repo.add_operator(Operator(None, n)) for n in [
        "Оператор «Альфа»", "Оператор «Бета»", "Оператор «Гамма»"]}
    for def_code, a, b, oper, region in [
        ("900", "0000000", "4999999", "Оператор «Альфа»", "77"),
        ("900", "5000000", "9999999", "Оператор «Бета»", "78"),
        ("903", "0000000", "9999999", "Оператор «Гамма»", "77"),
        ("904", "0000000", "4999999", "Оператор «Альфа»", "16"),
        ("904", "5000000", "9999999", "Оператор «Бета»", "50"),
    ]:
        repo.add_range(NumberRange(None, def_code, a, b, op[oper], reg[region]))
