"""Rolling price/time heatmap for displayed book liquidity."""

from collections import deque
from decimal import Decimal

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF


class LiquidityHeatmap(pg.PlotWidget):
    def __init__(self, tick: float = 0.01, columns: int = 420):
        super().__init__(title="LIQUIDITY · PRICE × TIME")
        self.tick, self.rows = Decimal(str(max(tick, 1e-9))), 121
        self.history, self.anchor = deque(maxlen=columns), None
        self.setLabel("bottom", "Replay time", units="s")
        self.setLabel("left", "Price")
        self.showGrid(x=True, y=True, alpha=0.12)
        self.setMenuEnabled(False)
        self.image = pg.ImageItem(axisOrder="row-major")
        self.image.setColorMap(pg.ColorMap([0, .5, 1], [(220, 70, 70), (13, 19, 27), (55, 205, 145)]))
        self.addItem(self.image)
        self.setBackground("#0d131b")

    def reset(self):
        self.history.clear(); self.anchor=None; self.image.clear()

    def push(self, book, t: float):
        mid = book.metrics().mid
        if mid is None: return
        center=(mid/self.tick).to_integral_value() * self.tick
        if self.anchor is None or abs(center-self.anchor)>self.tick*40:
            self.anchor=center; self.history.clear()
        levels = [self.anchor + (i-self.rows//2)*self.tick for i in range(self.rows)]
        column=([float(book.bids.get(p,0)) for p in levels],
                [float(book.asks.get(p,0)) for p in levels], t)
        if self.history and t < self.history[-1][2]: self.history.clear()
        if self.history and t == self.history[-1][2]: self.history[-1]=column
        else: self.history.append(column)
        data = np.array([np.subtract(b,a) for b,a,_ in self.history], dtype=np.float32).T
        limit = max(1.0, float(np.max(np.abs(data))))
        self.image.setImage(data, autoLevels=False, levels=(-limit,limit))
        first,last=self.history[0][2],self.history[-1][2]
        anchor,tick=float(self.anchor),float(self.tick)
        self.image.setRect(QRectF(first,anchor-tick*(self.rows//2),max(last-first,.01),tick*(self.rows-1)))
        self.setXRange(first,max(last,first+1),padding=0)
        self.setYRange(anchor-tick*50,anchor+tick*50,padding=0)
