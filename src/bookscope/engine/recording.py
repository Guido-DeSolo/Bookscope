"""JSONL recording loader; metadata lines are optional."""

import json
from decimal import DecimalException
from pathlib import Path

from bookscope.models import Event, from_record


def load(path: str | Path) -> tuple[dict, list[Event]]:
    metadata, events = {}, []
    with Path(path).open(encoding="utf-8") as source:
        for line_no, line in enumerate(source, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise TypeError("each JSONL line must be an object")
                if row.get("type") == "meta":
                    metadata.update(row)
                else:
                    event = from_record(row)
                    if events and event.t < events[-1].t:
                        raise ValueError("events must be ordered by t")
                    events.append(event)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError, DecimalException, AttributeError) as error:
                raise ValueError(f"{path}:{line_no}: {error}") from error
    if not events:
        raise ValueError(f"{path}: recording contains no events")
    metadata.pop("type", None)
    return metadata, events
