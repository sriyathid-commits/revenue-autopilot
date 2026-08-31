"""Utility functions for backend data processing and serialization."""

from __future__ import annotations

import math
from typing import Any


def sanitize_nan(obj: Any) -> Any:
    """Recursively convert NaN/Inf float values in dicts, lists, or primitives to 0.0 or None."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    elif isinstance(obj, dict):
        return {str(k): sanitize_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nan(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_nan(item) for item in obj)
    return obj
