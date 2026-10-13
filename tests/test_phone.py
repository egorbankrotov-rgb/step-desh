import pytest
from app.phone import parse_phone


@pytest.mark.parametrize("text", ["+7 (903) 123-45-67", "8 903 123 45 67", "9031234567"])
def test_parse_phone_formats(text):
    assert parse_phone(text) == ("903", "1234567")


@pytest.mark.parametrize("text", ["", "123", "+7 903 123", "abc"])
def test_parse_phone_invalid(text):
    with pytest.raises(ValueError):
        parse_phone(text)
