"""One deterministic event path for files and future live adapters."""

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from bookscope.engine.book import Metrics, OrderBook
from bookscope.models import Event, Trade


@dataclass(frozen=True, slots=True)
class Transition:
    event: Event
    before: Metrics
    after: Metrics


class MarketState:
    def __init__(self, trade_window: int = 600):
        self.book = OrderBook()
        self.trades: deque[Trade] = deque(maxlen=trade_window)

    def metrics(self) -> Metrics:
        return self.book.metrics()

    def apply(self, event: Event) -> Transition:
        before = self.metrics()
        if isinstance(event, Trade):
            self.trades.append(event)
        else:
            self.book.apply(event)
        return Transition(event, before, self.metrics())

    def flow(self, seconds: float = 5, now: float | None = None) -> tuple[Decimal, Decimal, Decimal | None, float]:
        if not self.trades:
            return Decimal(0), Decimal(0), None, 0.0
        end = self.trades[-1].t if now is None else now
        tape = [trade for trade in self.trades if end - trade.t <= seconds]
        if not tape: return Decimal(0), Decimal(0), None, 0.0
        buys = sum((x.size for x in tape if x.aggressor == "buy"), Decimal(0))
        sells = sum((x.size for x in tape if x.aggressor == "sell"), Decimal(0))
        total = buys + sells
        first = tape[0].t
        intensity = len(tape) / max(1.0, min(seconds, end - first))
        return buys, sells, (buys / total if total else None), intensity


class ReplayEngine:
    def __init__(self, events: list[Event]):
        if not events:
            raise ValueError("replay needs at least one event")
        self.events = events
        self.start = events[0].t
        self.cursor = 0
        self.target = 0.0
        self.state = MarketState()
        self.last_transition: Transition | None = None

    @property
    def done(self) -> bool:
        return self.cursor >= len(self.events)

    def step(self) -> Transition | None:
        if self.done:
            return None
        event = self.events[self.cursor]
        self.last_transition = self.state.apply(event)
        self.cursor += 1
        self.target = max(self.target, event.t - self.start)
        return self.last_transition

    def advance(self, seconds: float) -> int:
        self.target = min(max(0.0, self.target + seconds), self.events[-1].t - self.start)
        count = 0
        while not self.done and self.events[self.cursor].t <= self.start + self.target:
            self.step()
            count += 1
        return count

    def seek(self, index: int) -> None:
        self.target = 0.0
        self.state, self.last_transition = MarketState(), None
        self.cursor = 0
        for event in self.events[:max(0, min(index, len(self.events)))]:
            self.last_transition = self.state.apply(event)
            self.cursor += 1
        self.target = (self.events[self.cursor - 1].t - self.start) if self.cursor else 0.0
