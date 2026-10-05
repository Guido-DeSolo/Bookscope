import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from bookscope.engine.book import OrderBook
from bookscope.engine.recording import load
from bookscope.engine.replay import MarketState, ReplayEngine
from bookscope.generate import generate
from bookscope.models import BookUpdate, Snapshot, from_record


class OrderBookTests(unittest.TestCase):
    def setUp(self):
        self.book=OrderBook()
        self.book.apply(Snapshot(0,((Decimal(100),Decimal(4)),(Decimal("99.99"),Decimal(6))),
                                 ((Decimal("100.02"),Decimal(2)),(Decimal("100.03"),Decimal(8)))))

    def test_snapshot_metrics_include_depth_imbalance_spread_and_microprice(self):
        m=self.book.metrics()
        self.assertEqual((m.bid,m.ask,m.spread,m.mid),tuple(map(Decimal,("100","100.02","0.02","100.01"))))
        self.assertEqual((m.bid_depth,m.ask_depth,m.imbalance),(Decimal(10),Decimal(10),Decimal(0)))
        self.assertAlmostEqual(float(m.microprice),100.0133333333)

    def test_zero_size_removes_level_and_reveals_next_quote(self):
        self.book.apply(BookUpdate(1,"bid",Decimal(100),Decimal(0)))
        self.assertEqual(self.book.metrics().bid,Decimal("99.99"))
        self.assertNotIn(Decimal(100),self.book.bids)

    def test_trade_event_does_not_fabricate_book_change(self):
        state=MarketState(); state.book=self.book
        state.apply(from_record({"t":1,"type":"trade","side":"buy","price":100.02,"size":1}))
        self.assertEqual(state.book.metrics().ask,Decimal("100.02"))


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.events=[from_record(x) for x in (
            {"t":0,"type":"snapshot","bids":[[100,3]],"asks":[[100.01,2]]},
            {"t":1,"type":"book","side":"bid","price":100,"size":0},
            {"t":1.1,"type":"trade","side":"sell","price":99.99,"size":.4},
            {"t":2,"type":"book","side":"bid","price":99.99,"size":4})]

    def test_seek_and_step_reconstruct_identical_state(self):
        engine=ReplayEngine(self.events); engine.advance(2)
        result=(dict(engine.state.book.bids),engine.state.flow())
        engine.seek(2); engine.step(); engine.step()
        self.assertEqual((dict(engine.state.book.bids),engine.state.flow()),result)

    def test_transition_inspector_captures_before_and_after(self):
        engine=ReplayEngine(self.events); engine.advance(1)
        event=engine.last_transition
        self.assertEqual(event.before.bid,100)
        self.assertIsNone(event.after.bid)

    def test_trade_flow_counts_aggressor_volume(self):
        engine=ReplayEngine(self.events); engine.advance(2)
        buys,sells,share,_=engine.state.flow()
        self.assertEqual((buys,sells,share),(Decimal(0),Decimal("0.4"),Decimal(0)))
        self.assertIsNone(engine.state.flow(now=10)[2])

    def test_recording_loader_checks_order_and_reads_metadata(self):
        rows=[{"type":"meta","symbol":"XYZ"},{"t":0,"type":"snapshot","bids":[[10,1]],"asks":[[11,1]]}]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"sample.jsonl"; path.write_text("\n".join(json.dumps(x) for x in rows))
            meta,events=load(path); self.assertEqual(meta["symbol"],"XYZ"); self.assertEqual(len(events),1)
            late={"t":2,"type":"trade","side":"buy","price":11,"size":1}
            early={"t":1,"type":"trade","side":"sell","price":10,"size":1}
            path.write_text(json.dumps(late)+"\n"+json.dumps(early))
            with self.assertRaisesRegex(ValueError,"ordered by t"):
                load(path)
            path.write_text(json.dumps(rows[1])+"\n"+json.dumps({"t":-1,"type":"trade","side":"buy","price":1,"size":1}))
            with self.assertRaisesRegex(ValueError,"event time"):
                load(path)

    def test_generated_demo_replays_a_visible_liquidity_shock(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"shock.jsonl"; count=generate(path)
            metadata,events=load(path); engine=ReplayEngine(events)
            engine.seek(2)
            calm=engine.state.book.metrics()
            engine.seek(count)
            shock=engine.state.book.metrics()
            self.assertEqual(metadata["symbol"],"BTC/USD · SIMULATED")
            self.assertGreater(shock.spread,calm.spread)
            self.assertLess(shock.imbalance,calm.imbalance)


if __name__=="__main__": unittest.main()
