"""Incremental limit-order-book state and microstructure metrics."""

from dataclasses import dataclass
from decimal import Decimal

from bookscope.models import BookUpdate, Snapshot

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Metrics:
    bid: Decimal | None
    ask: Decimal | None
    spread: Decimal | None
    mid: Decimal | None
    microprice: Decimal | None
    bid_depth: Decimal
    ask_depth: Decimal
    imbalance: Decimal | None


class OrderBook:
    def __init__(self):
        self.bids: dict[Decimal, Decimal] = {}
        self.asks: dict[Decimal, Decimal] = {}

    def apply(self, event: BookUpdate | Snapshot) -> None:
        if isinstance(event, Snapshot):
            self.bids = {p: q for p, q in event.bids if q > 0}
            self.asks = {p: q for p, q in event.asks if q > 0}
            return
        if event.side not in {"bid", "ask"} or event.price <= 0 or event.size < 0:
            raise ValueError("book update requires a valid side, positive price, and nonnegative size")
        side = self.bids if event.side == "bid" else self.asks
        if event.size == 0:
            side.pop(event.price, None)
        else:
            side[event.price] = event.size

    def levels(self, side: str, count: int = 10) -> list[tuple[Decimal, Decimal]]:
        book = self.bids if side == "bid" else self.asks
        return sorted(book.items(), reverse=side == "bid")[:count]

    def metrics(self, count: int = 10) -> Metrics:
        bid = max(self.bids, default=None)
        ask = min(self.asks, default=None)
        bd = sum((q for _, q in self.levels("bid", count)), ZERO)
        ad = sum((q for _, q in self.levels("ask", count)), ZERO)
        total = bd + ad
        mid = (bid + ask) / 2 if bid is not None and ask is not None else None
        micro = ((ask * self.bids[bid] + bid * self.asks[ask]) / (self.bids[bid] + self.asks[ask])
                 if bid is not None and ask is not None and self.bids[bid] + self.asks[ask] else None)
        return Metrics(bid, ask, ask - bid if mid is not None else None, mid, micro,
                       bd, ad, (bd - ad) / total if total else None)
