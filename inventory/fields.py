"""Custom form fields for the inventory app."""

import calendar
import re
from datetime import date

from django import forms


class FlexibleExpiryDateField(forms.Field):
    """A date field that accepts either a full date or just month/year.

    Accepted formats (separators '/', '-', or '.' all work):
    - Full date: DD/MM/YY or DD/MM/YYYY, e.g. '21/08/26' or '21/08/2026'
    - Month only: MM/YY or MM/YYYY, e.g. '08/26' or '08/2026' -- since many
      packaged goods only print a month/year expiry, this is automatically
      treated as the LAST day of that month (the safer assumption for an
      expiry date), e.g. '08/26' -> 31 Aug 2026.

    Two-digit years are assumed to be 20XX. Also accepts ISO 'YYYY-MM-DD'
    (e.g. from a native date picker or existing stored values) for
    backward compatibility.
    """

    widget = forms.TextInput(
        attrs={"placeholder": "DD/MM/YY or MM/YY, e.g. 21/08/26 or 08/26"}
    )
    default_error_messages = {
        "invalid": (
            "Enter a full date as DD/MM/YY (e.g. 21/08/26) or a month/year "
            "only as MM/YY (e.g. 08/26)."
        ),
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text:
            return None

        normalized = re.sub(r"[.\-\s]", "/", text)
        parts = [p for p in normalized.split("/") if p != ""]

        try:
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    # YYYY/MM/DD (ISO-style, e.g. from stored/legacy values)
                    year, month, day = (int(p) for p in parts)
                else:
                    # DD/MM/YY or DD/MM/YYYY
                    day, month, year = (int(p) for p in parts)
                    year = self._expand_year(year)
                return date(year, month, day)

            if len(parts) == 2:
                if len(parts[0]) == 4:
                    # YYYY/MM
                    year, month = (int(p) for p in parts)
                else:
                    # MM/YY or MM/YYYY -- month only, use last day of month
                    month, year = (int(p) for p in parts)
                    year = self._expand_year(year)
                last_day = calendar.monthrange(year, month)[1]
                return date(year, month, last_day)
        except (ValueError, calendar.IllegalMonthError):
            pass

        raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    @staticmethod
    def _expand_year(year):
        return year + 2000 if year < 100 else year

    def prepare_value(self, value):
        """Render an existing date back as DD/MM/YYYY when editing."""
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        return value
