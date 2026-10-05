"""Dense replay workstation."""

from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bookscope import __version__
from bookscope.engine.recording import load
from bookscope.engine.replay import ReplayEngine
from bookscope.ui.heatmap import LiquidityHeatmap

BG,PANEL,TEXT,GREEN,RED,CYAN="#0b1017","#101923","#d4dde7","#38d996","#ff657a","#59c8ff"


def cell(text, color=TEXT, align=Qt.AlignmentFlag.AlignRight):
    result=QTableWidgetItem(text); result.setForeground(pg.mkColor(color))
    result.setTextAlignment(align|Qt.AlignmentFlag.AlignVCenter); return result


class Workstation(QMainWindow):
    def __init__(self, recording: Path):
        super().__init__(); self.setWindowTitle(f"Bookscope · {__version__}"); self.resize(1480,920)
        self.meta,self.events=load(recording); self.engine=ReplayEngine(self.events); self.speed=1
        self.timer=QTimer(self); self.timer.setInterval(33); self.timer.timeout.connect(self.pulse)
        self._build(recording); self.seek(self.initial_count())

    def initial_count(self):
        return next((i for i,event in enumerate(self.events) if event.t>self.engine.start),len(self.events))

    def _build(self, recording):
        root=QWidget(); root.setStyleSheet(f"background:{BG};color:{TEXT};font:12px 'DejaVu Sans Mono'")
        layout=QVBoxLayout(root); layout.setContentsMargins(12,10,12,10); layout.setSpacing(8)
        header=QHBoxLayout(); title=QLabel("BOOKSCOPE  /  MARKET MICROSTRUCTURE")
        title.setStyleSheet(f"color:{CYAN};font-size:18px;font-weight:bold")
        self.symbol=QLabel(self.meta.get("symbol","SAMPLE")); self.symbol.setStyleSheet("font-size:20px;font-weight:bold")
        self.file_label=QLabel(recording.name); self.file_label.setStyleSheet("color:#8291a3")
        open_button=QPushButton("OPEN RECORDING"); open_button.clicked.connect(self.open_recording)
        header.addWidget(title); header.addStretch(); header.addWidget(self.symbol); header.addWidget(self.file_label); header.addWidget(open_button); layout.addLayout(header)
        self.metrics={}; strip=QHBoxLayout()
        for name in ("SPREAD","IMBALANCE","MICROPRICE","MICRO Δ","BUY FLOW","TRADES/SEC"):
            box=QVBoxLayout(); cap=QLabel(name); cap.setStyleSheet("color:#8291a3;font-size:10px")
            value=QLabel("—"); value.setStyleSheet(f"color:{TEXT};font-size:17px;font-weight:bold")
            box.addWidget(cap); box.addWidget(value); strip.addLayout(box); self.metrics[name]=value
        layout.addLayout(strip)

        split=QSplitter(Qt.Orientation.Horizontal)
        self.ladder=QTableWidget(21,3); self.ladder.setHorizontalHeaderLabels(["ASK SIZE","PRICE","BID SIZE"])
        self.ladder.verticalHeader().hide(); self.ladder.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ladder.setSelectionMode(QTableWidget.SelectionMode.NoSelection); self.ladder.setAlternatingRowColors(True)
        self.ladder.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ladder.setStyleSheet(f"QTableWidget{{background:{PANEL};alternate-background-color:#131e29;gridline-color:#253342;border:0}} QHeaderView::section{{background:#182431;color:#91a5b8;border:0;padding:5px}}")
        self.ladder.horizontalHeader().setStretchLastSection(True); self.ladder.horizontalHeader().setDefaultSectionSize(105); split.addWidget(self.ladder)
        right=QWidget(); grid=QGridLayout(right); grid.setContentsMargins(4,0,0,0); grid.setSpacing(8)
        self.depth=pg.PlotWidget(title="DEPTH PROFILE"); self.depth.setBackground(PANEL)
        self.depth.setLabel("bottom","Cumulative size"); self.depth.setLabel("left","Price")
        self.depth.showGrid(x=True,y=True,alpha=.12); self.depth.setMenuEnabled(False)
        self.heat=LiquidityHeatmap(float(self.meta.get("tick_size",.01)))
        self.tape=QTableWidget(12,4); self.tape.setHorizontalHeaderLabels(["TIME","FLOW","SIZE","PRICE"])
        self.tape.verticalHeader().hide(); self.tape.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tape.setSelectionMode(QTableWidget.SelectionMode.NoSelection); self.tape.horizontalHeader().setStretchLastSection(True)
        self.tape.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for column,width in enumerate((80,78,74,110)): self.tape.setColumnWidth(column,width)
        self.tape.setStyleSheet(f"QTableWidget{{background:{PANEL};gridline-color:#253342;border:0}} QHeaderView::section{{background:#182431;color:#91a5b8;border:0;padding:4px}}")
        self.inspector=QPlainTextEdit(); self.inspector.setReadOnly(True); self.inspector.setMaximumHeight(136)
        self.inspector.setStyleSheet(f"background:{PANEL};border:0;color:{TEXT};padding:8px")
        grid.addWidget(self.depth,0,0); grid.addWidget(self.heat,1,0); grid.addWidget(self.tape,0,1); grid.addWidget(self.inspector,1,1)
        grid.setColumnStretch(0,3); grid.setColumnStretch(1,2); grid.setRowStretch(0,1); grid.setRowStretch(1,1)
        split.addWidget(right); split.setStretchFactor(0,1); split.setStretchFactor(1,4); split.setSizes([390,1090]); layout.addWidget(split,1)

        controls=QHBoxLayout(); self.toggle=QPushButton("▶ PLAY"); self.toggle.clicked.connect(self.toggle_play)
        step=QPushButton("STEP ▸"); step.clicked.connect(self.step)
        self.speeds=QComboBox(); self.speeds.addItems(["1×","2×","10×","100×"])
        self.speeds.currentIndexChanged.connect(lambda i:setattr(self,"speed",(1,2,10,100)[i]))
        self.slider=QSlider(Qt.Orientation.Horizontal); self.slider.setRange(0,len(self.events)); self.slider.valueChanged.connect(self.seek)
        self.clock=QLabel("00:00.000"); controls.addWidget(self.toggle); controls.addWidget(step); controls.addWidget(self.speeds)
        controls.addWidget(self.slider,1); controls.addWidget(self.clock); layout.addLayout(controls); self.setCentralWidget(root)

    def open_recording(self):
        path,_=QFileDialog.getOpenFileName(self,"Open JSONL recording",str(Path.home()),"JSONL recordings (*.jsonl);;All files (*)")
        if not path: return
        try: metadata,events=load(path)
        except (OSError,ValueError) as error:
            QMessageBox.warning(self,"Could not open recording",str(error)); return
        self.timer.stop(); self.meta,self.events=metadata,events; self.engine=ReplayEngine(self.events)
        self.symbol.setText(self.meta.get("symbol","UNKNOWN")); self.file_label.setText(Path(path).name)
        self.slider.blockSignals(True); self.slider.setRange(0,len(self.events)); self.slider.setValue(0); self.slider.blockSignals(False)
        self.heat=LiquidityHeatmap(float(self.meta.get("tick_size",.01)))
        grid=self.depth.parentWidget().layout(); old=grid.itemAtPosition(1,0).widget()
        grid.replaceWidget(old,self.heat); old.setParent(None); old.deleteLater()
        self.seek(self.initial_count())

    def toggle_play(self):
        if self.timer.isActive(): self.timer.stop(); self.toggle.setText("▶ PLAY")
        else: self.timer.start(); self.toggle.setText("❚❚ PAUSE")

    def step(self):
        self.timer.stop(); self.toggle.setText("▶ PLAY"); self.engine.step(); self.sync_slider(); self.render()

    def pulse(self):
        self.engine.advance(self.timer.interval()/1000*self.speed); self.sync_slider(); self.render()
        if self.engine.done: self.toggle_play()

    def sync_slider(self):
        self.slider.blockSignals(True); self.slider.setValue(self.engine.cursor); self.slider.blockSignals(False)

    def seek(self,index):
        self.engine.seek(index); self.sync_slider(); self.render()

    def render(self):
        state,book=self.engine.state,self.engine.state.book; m=book.metrics()
        _,_,share,intensity=state.flow(now=self.engine.start+self.engine.target)
        values={"SPREAD":f"{m.spread:.4f}" if m.spread is not None else "—",
          "IMBALANCE":f"{m.imbalance:+.1%}" if m.imbalance is not None else "—",
          "MICROPRICE":f"{m.microprice:,.4f}" if m.microprice is not None else "—",
          "MICRO Δ":f"{m.microprice-m.mid:+.4f}" if m.microprice is not None and m.mid is not None else "—",
          "BUY FLOW":f"{share:.0%} BUY" if share is not None else "—","TRADES/SEC":f"{intensity:.1f}"}
        for key,value in values.items(): self.metrics[key].setText(value)
        asks,bids=book.levels("ask",10),book.levels("bid",10)
        prices=sorted({p for p,_ in asks+bids},reverse=True)[:21]; amap,bmap=dict(asks),dict(bids)
        for i in range(21):
            p=prices[i] if i<len(prices) else None; a=amap.get(p) if p else None; b=bmap.get(p) if p else None
            self.ladder.setItem(i,0,cell(f"{a:.4f}" if a is not None else "",RED))
            self.ladder.setItem(i,1,cell(f"{p:,.4f}" if p is not None else "",CYAN))
            self.ladder.setItem(i,2,cell(f"{b:.4f}" if b is not None else "",GREEN))
        self.depth.clear()
        for side,color in (("bid",GREEN),("ask",RED)):
            levels=book.levels(side,12); cumulative=0; ys=[]; xs=[]
            for price,size in levels: cumulative+=float(size); ys.append(float(price)); xs.append(cumulative)
            if xs: self.depth.plot(xs,ys,pen=pg.mkPen(color,width=2))
        tape=list(state.trades)[-12:][::-1]
        for i in range(12):
            tr=tape[i] if i<len(tape) else None; buy=tr and tr.aggressor=="buy"
            self.tape.setItem(i,0,cell(f"{tr.t:10.3f}" if tr else "",align=Qt.AlignmentFlag.AlignLeft))
            self.tape.setItem(i,1,cell(("▲ BUY" if buy else "▼ SELL") if tr else "",GREEN if buy else RED))
            self.tape.setItem(i,2,cell(f"{tr.size:g}" if tr else "")); self.tape.setItem(i,3,cell(f"{tr.price:,.4f}" if tr else ""))
        if self.engine.last_transition:
            tr=self.engine.last_transition; a,b=tr.before,tr.after
            def fmt(value,percent=False):
                return "—" if value is None else f"{value:+.1%}" if percent else f"{value:,.4f}"
            e=tr.event
            detail=(f"{e.aggressor.upper()} {e.size:g} @ {e.price:,.4f}" if hasattr(e,"aggressor") else
                    f"{e.side.upper()} {e.price:,.4f} → {e.size:g}" if hasattr(e,"side") else
                    f"snapshot · {len(e.bids)} bids / {len(e.asks)} asks")
            self.inspector.setPlainText(f"EVENT {self.engine.cursor:,} · {type(e).__name__.upper()} · t={e.t:.4f}\n"
              f"BEFORE  bid {fmt(a.bid)}  ask {fmt(a.ask)}  spread {fmt(a.spread)}  imbalance {fmt(a.imbalance,True)}\n"
              f"AFTER   bid {fmt(b.bid)}  ask {fmt(b.ask)}  spread {fmt(b.spread)}  imbalance {fmt(b.imbalance,True)}\n{detail}")
        self.clock.setText(f"{self.engine.target:08.3f}s / {self.engine.cursor:,} events")
        if m.mid is not None: self.heat.push(book,self.engine.target)
        else: self.heat.reset()
