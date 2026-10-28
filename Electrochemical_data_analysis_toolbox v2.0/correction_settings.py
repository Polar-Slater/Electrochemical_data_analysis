"""Shared validation and provenance for offline potential corrections."""
import math
import re
from pathlib import Path


def finite_number(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} must be a finite number.") from None
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    return number


def positive_area(value):
    area = finite_number(value, "Working area")
    if area <= 0:
        raise ValueError("Working area must be greater than zero.")
    return area


def validate_ir(resistance, percent, *, require_resistance=True):
    percent = finite_number(percent, "Compensation level")
    if not 0 <= percent <= 100:
        raise ValueError("Compensation level must be between 0 and 100 percent.")
    if resistance is not None:
        resistance = finite_number(resistance, "Solution resistance")
        if resistance < 0:
            raise ValueError("Solution resistance cannot be negative.")
    if require_resistance and percent > 0 and resistance is None:
        raise ValueError("Nonzero compensation requires a solution resistance; enter Rs or supply it in the LSV filename.")
    return resistance, percent / 100


def parse_ir_fields(raw_rs, raw_percent):
    """Read optional GUI fields, requiring a percentage when Rs is entered."""
    raw_rs, raw_percent = raw_rs.strip(), raw_percent.strip()
    if not raw_rs and not raw_percent:
        return None
    if not raw_percent:
        raise ValueError("Enter a compensation percentage, or clear both iR fields.")
    return validate_ir(raw_rs or None, raw_percent)


def resistance_from_filename(path):
    # Include the sign/exponent so '-2 ohm' cannot be mistaken for '+2 ohm'.
    match = re.search(r"(?<![A-Za-z0-9.])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)\s*ohm\b",
                      Path(path).stem, re.IGNORECASE)
    if match is None:
        return None
    return validate_ir(match[1], 0)[0]


def resolve_lsv_resistance(path, explicit, percent):
    resistance = explicit if explicit is not None else resistance_from_filename(path)
    resistance, fraction = validate_ir(resistance, percent)
    source = "explicit" if explicit is not None else "filename" if resistance is not None else "not supplied"
    return resistance, fraction, source


def ir_applied(resistance, fraction):
    return resistance is not None and resistance > 0 and fraction is not None and fraction > 0


def ir_metadata(resistance, fraction, source):
    return ["Resistance source", source, "iR correction applied", "yes" if ir_applied(resistance, fraction) else "no"]
