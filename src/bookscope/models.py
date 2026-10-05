"""Normalized, exchange-neutral market events."""

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from typing import TypeAlias

Number: TypeAlias = Decimal


@dataclass(frozen=True, slots=True)
class BookUpdate:
    t: float
    side: str
    price: Number
    size: Number


@dataclass(frozen=True, slots=True)
class Trade:
    t: float
    price: Number
    size: Number
    aggressor: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    t: float
    bids: tuple[tuple[Number, Number], ...]
    asks: tuple[tuple[Number, Number], ...]


Event: TypeAlias = BookUpdate | Trade | Snapshot


def from_record(row: dict) -> Event:
    t, kind = float(row["t"]), row["type"].lower()
    if not isfinite(t) or t < 0:
        raise ValueError("event time must be nonnegative")
    if kind == "book":
        side = row["side"].lower()
        if side not in {"bid", "ask"}:
            raise ValueError(f"invalid book side: {side}")
        price, size = Decimal(str(row["price"])), Decimal(str(row["size"]))
        if not price.is_finite() or not size.is_finite() or price <= 0 or size < 0:
            raise ValueError("book price must be positive and size nonnegative")
        return BookUpdate(t, side, price, size)
    if kind == "trade":
        side = str(row.get("aggressor", row.get("side", ""))).lower()
        price, size = Decimal(str(row["price"])), Decimal(str(row["size"]))
        if side not in {"buy", "sell"} or not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0:
            raise ValueError("trade requires buy/sell aggressor, positive price and size")
        return Trade(t, price, size, side)
    if kind == "snapshot":
        def levels(name: str) -> tuple[tuple[Number, Number], ...]:
            result = tuple((Decimal(str(p)), Decimal(str(q))) for p, q in row[name])
            if any(p <= 0 or q < 0 or not p.is_finite() or not q.is_finite() for p, q in result):
                raise ValueError("snapshot prices must be positive and sizes nonnegative")
            return result
        return Snapshot(t, levels("bids"), levels("asks"))
    raise ValueError(f"unknown event type: {kind}")
