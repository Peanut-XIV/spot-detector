import unicodedata
from math import isfinite
from typing import Annotated

from pydantic import BeforeValidator

# bump SCHEMA_VERSION in config_fingerprint.py
# if SIGNIFICANT_DIGITS needs to change
SIGNIFICANT_DIGITS = 6

type JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


def quantize_float(value: object) -> object:
    """Reduce a float to SIGNIFICANT_DIGITS significant digits.

    Exponential notation is preferred over rounding to N decimal places, which
    would flatten very small quantities to zero: the minimum occupation of the
    signal mask sits around 1e-4 and nothing forbids a future quantity from
    going lower. Adding 0.0 turns -0.0 into 0.0, the two being equal yet
    yielding two different fingerprints.

    Non-finite values are rejected here rather than at serialization time: NaN
    equals no value at all, not even itself, and has no place in a
    configuration.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    number = float(value) + 0.0
    if not isfinite(number):
        raise ValueError("non-finite value in configuration")
    return float(f"{number:.{SIGNIFICANT_DIGITS - 1}e}")


CanonicalFloat = Annotated[float, BeforeValidator(quantize_float)]
"""Annotation to put on the float fields of the models.

Quantizing at setting time rather than at digest time puts normalization at the
entry boundary of the model, where dubious values arrive. The displayed value,
the stored value and the digested value then become the same one. Remember to
enable `validate_assignment` on the models involved: without it, an assignment
made after construction bypasses validation, and the interface writes in
exactly that way.
"""


def canonical_repr(value: object) -> JSONValue:
    """Recursively normalize a structure before serialization."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return quantize_float(value)  # pyright: ignore[reportReturnType]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)):
        return [canonical_repr(item) for item in value]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): canonical_repr(item)  # pyright: ignore[reportUnknownArgumentType]
            for key, item in value.items()  # pyright: ignore[reportUnknownVariableType]
        }
    raise TypeError(f"unserializable type in the canonical view: {type(value)!r}")
