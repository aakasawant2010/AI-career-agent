"""Datetime helpers.

SQLite hands back naive datetimes even for DateTime(timezone=True) columns while
Postgres returns aware ones. Everything that compares or subtracts stored
timestamps goes through ``as_utc`` so both backends behave the same.
"""

from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
