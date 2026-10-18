"""CSV generation and sanitization logic to prevent CSV formula injection."""

from __future__ import annotations

import csv
import io
from typing import Any, Sequence


def sanitize_csv_value(value: Any) -> str:
    """Sanitize a value for safe CSV export.

    Guards against CSV formula injection (OWASP CSV Injection):
    If a string begins with '=', '+', '-', '@', tab, or carriage return,
    prefix it with a single quote (') so spreadsheet applications interpret
    it as text rather than an executable formula.
    """
    if value is None:
        return ""

    str_val = str(value)
    if not str_val:
        return ""

    dangerous_prefixes = ("=", "+", "-", "@", "\t", "\r")
    if str_val.startswith(dangerous_prefixes):
        return f"'{str_val}"

    return str_val


def generate_csv_content(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> str:
    """Generate RFC 4180 compliant CSV string from headers and sequence of row tuples/lists.

    All cell values are sanitized to prevent CSV injection.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write headers
    writer.writerow([sanitize_csv_value(h) for h in headers])

    # Write rows
    for row in rows:
        writer.writerow([sanitize_csv_value(val) for val in row])

    return output.getvalue()
