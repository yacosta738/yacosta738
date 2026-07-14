import datetime
from profile_card import format_plural, uptime_string


def test_format_plural_returns_empty_suffix_for_one():
    assert format_plural(1) == ""


def test_format_plural_returns_s_suffix_for_zero_and_many():
    assert format_plural(0) == "s"
    assert format_plural(5) == "s"


def test_uptime_string_formats_years_months_days():
    start = datetime.date(2012, 9, 3)
    today = datetime.date(2015, 9, 3)  # exactly 3 years later
    assert uptime_string(start, today) == "3 years, 0 months, 0 days"


def test_uptime_string_uses_singular_units_when_value_is_one():
    start = datetime.date(2012, 9, 3)
    today = datetime.date(2013, 10, 4)  # 1 year, 1 month, 1 day later
    assert uptime_string(start, today) == "1 year, 1 month, 1 day"
