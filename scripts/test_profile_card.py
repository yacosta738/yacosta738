import datetime
from unittest.mock import patch

from profile_card import fetch_commit_count, format_plural, uptime_string


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


def test_fetch_commit_count_splits_requests_into_one_year_windows():
    response = {
        "data": {"user": {"contributionsCollection": {"totalCommitContributions": 7}}}
    }
    with patch("profile_card.graphql_request", return_value=response) as request:
        assert fetch_commit_count("yacosta738", years_back=3) == 21

    assert request.call_count == 3
    for call in request.call_args_list:
        start = datetime.datetime.fromisoformat(call.args[1]["start"].replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(call.args[1]["end"].replace("Z", "+00:00"))
        assert end - start <= datetime.timedelta(days=365)
