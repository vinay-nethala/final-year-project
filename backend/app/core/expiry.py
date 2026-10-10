from datetime import date, datetime, timezone
from typing import Optional

def get_current_date() -> date:
    """Returns today's date in local time for consistent expiry calculations."""
    return date.today()

def calculate_days_until_expiry(expiry_date: date, current_date: Optional[date] = None) -> int:
    """
    Computes integer days remaining until expiry.
    If expiry_date == current_date, returns 0 (same-day clearance).
    If expiry_date < current_date, returns negative value (already expired).
    """
    if current_date is None:
        current_date = get_current_date()
    return (expiry_date - current_date).days

def get_expiry_urgency_band(days_until_expiry: int) -> str:
    """
    Standard display urgency bands:
    - 'EXPIRED': days < 0
    - 'CRITICAL' (Red): 0 <= days <= 2
    - 'WARNING' (Yellow): 3 <= days <= 5
    - 'NORMAL' (Green): days > 5
    """
    if days_until_expiry < 0:
        return "EXPIRED"
    elif days_until_expiry <= 2:
        return "CRITICAL"
    elif days_until_expiry <= 5:
        return "WARNING"
    else:
        return "NORMAL"
