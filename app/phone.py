import re


def parse_phone(text: str) -> tuple[str, str]:
    """'+7 (903) 123-45-67' -> ('903', '1234567')."""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError("Введите номер в формате +7 (XXX) XXX-XX-XX.")
    return digits[:3], digits[3:]
