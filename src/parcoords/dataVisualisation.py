import importlib
import json
import tempfile
from pathlib import Path
from typing import List

import numpy as np
import plotly.colors as pcol
import plotly.graph_objects as go
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from tabulate import tabulate

from parcoords.dataAnalysis import getMetaMatrix

QtWebEngineWidgets = importlib.import_module(pg.Qt.lib + ".QtWebEngineWidgets")
DBG_DONTBLOCK = False


class parCoordDockArea(DockArea):
    def __init__(self, noDataView=False):
        super().__init__()
        self.pc = pc = ParCoordWidget()
        pcd = Dock("parcoords")

        pcd.addWidget(pc)
        self.addDock(pcd, "top")

        if not noDataView:
            pd = Dock("plots")
            self.plts = plts = FilteredPlots(self.pc)
            pd.addWidget(plts)
            self.addDock(pd, "bottom")

        stats = Dock("stats")
        self.statswidget = StatsWidget(self.pc)
        stats.addWidget(self.statswidget)
        self.addDock(stats, "below", pcd)

        pcd.raiseDock()

        self.ld = ListDock(pc)
        self.addDock(self.ld, "left")

    def setParcoordData(self, dfs, calculator=None):
        self.pc.setParcoordData(dfs, calculator)


class ListDock(Dock):
    selectionChanged = QtCore.Signal(object)

    def __init__(self, pc):
        super().__init__("data list")
        self.parcoords = pc
        self.view = QtWidgets.QTreeView()
        self.mdl = QtGui.QStandardItemModel()
        self.view.setModel(self.mdl)
        self.setMaximumWidth(250)
        self.addWidget(self.view)
        self.parcoords.datachanged.connect(self.setdata)
        self.view.selectionModel().selectionChanged.connect(self.emitCurrentNode)

    def setdata(self):
        self.mdl.clear()
        self.mdl.setHorizontalHeaderLabels(["#", "name"])
        self.view.setAlternatingRowColors(True)
        root = self.mdl.invisibleRootItem()
        for idx, k in enumerate(self.parcoords.dfs.keys()):
            i1 = QtGui.QStandardItem(str(idx))
            i1.setEditable(False)
            i1.setToolTip(k)
            i2 = QtGui.QStandardItem(k)
            i2.setEditable(False)
            i2.setToolTip(k)
            root.appendRow([i1, i2])

    def emitCurrentNode(self):
        selectedIDX = self.view.selectedIndexes()
        if len(selectedIDX) < 1:
            return
        else:
            selectedIDX = selectedIDX[0]
        selectedItem = self.mdl.itemFromIndex(selectedIDX)
        self.selectionChanged.emit(selectedItem)


class HistDock(Dock):
    def __init__(self):
        super().__init__("metadata histograms")
        self.plt = pg.GraphicsLayoutWidget()
        self.sel = pg.QtWidgets.QComboBox()
        self.addWidget(self.sel)
        self.addWidget(self.plt)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.sel.currentTextChanged.connect(self.updateData)

    def setData(self, parcoords):
        ks = tuple(parcoords.minmax.keys())
        self.pc = parcoords
        self.sel.addItems(ks)
        self.sel.setCurrentText(ks[0])
        self.updateData()

    def updateData(self):
        sel = self.sel.currentText()
        hist, histEdges = np.histogram(self.pc.meta[sel])
        self.plt.clear()
        p1 = self.plt.addPlot()
        p1.showGrid(1, 1, 0.6)
        p1.setLabel("bottom", "value")
        p1.setLabel("left", "cnt")

        xs = (histEdges[:-1] + histEdges[1:]) / 2
        w = histEdges[1] - histEdges[0]
        bi = pg.BarGraphItem(x=xs, height=hist, width=w, brush="r")
        p1.addItem(bi)


class BarDock(Dock):
    def __init__(self):
        super().__init__("metadata bardiags")
        self.plt = pg.GraphicsLayoutWidget()
        self.sel = pg.QtWidgets.QComboBox()
        self.plt2 = pg.GraphicsLayoutWidget()
        self.sel2 = pg.QtWidgets.QComboBox()
        self.addWidget(self.sel)
        self.addWidget(self.plt)
        self.addWidget(self.sel2)
        self.addWidget(self.plt2)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.sel.currentTextChanged.connect(self.updateData)
        self.sel2.currentTextChanged.connect(self.updateData)

    def setData(self, parcoords):
        ks = tuple(parcoords.minmax.keys())
        self.pc = parcoords
        self.sel.addItems(ks)
        self.sel.setCurrentText(ks[0])
        self.sel2.addItems(ks)
        self.sel2.setCurrentText(ks[1])
        self.updateData()

    def updateData(self):
        self.plt.clear()
        self.plt2.clear()

        sel = self.sel.currentText()
        if not sel:
            return

        p1 = self.plt.addPlot()
        p1.showGrid(1, 1, 0.6)
        p1.setLabel("bottom", "dataset")
        p1.setLabel("left", "val")

        xs = range(len(self.pc.dfs))
        ys = [x.attrs[sel] for x in self.pc.dfs.values()]
        bi = pg.BarGraphItem(x=xs, height=ys, width=0.9, brush="r")
        p1.addItem(bi)

        sel2 = self.sel2.currentText()
        if not sel2:
            return

        p2 = self.plt2.addPlot()
        p2.showGrid(1, 1, 0.6)
        p2.setLabel("bottom", "dataset")
        p2.setLabel("left", "val")

        xs = range(len(self.pc.dfs))
        ys = [x.attrs[sel2] for x in self.pc.dfs.values()]
        bi = pg.BarGraphItem(x=xs, height=ys, width=0.9, brush="r")
        p2.addItem(bi)
        p1.setXLink(p2)


class StatsWidget(DockArea):
    def __init__(self, parcoords):
        super().__init__()

        self.pc = parcoords
        self.pc.datachanged.connect(self.createStats)

        self.table = QtWidgets.QPlainTextEdit()
        f = self.table.font()
        f.setFamily("monospace")
        f.setStyleHint(QtGui.QFont.TypeWriter)
        self.table.setFont(f)
        self.tableDock = Dock("metadata table")
        self.tableDock.addWidget(self.table)
        self.addDock(self.tableDock, "left")

        self.HistDock = HistDock()
        self.addDock(self.HistDock, "right")
        self.BarDock = BarDock()
        self.addDock(self.BarDock, "below", self.HistDock)

    def createStats(self):

        self.table.clear()

        self.dfs = self.pc.dfs
        minmaxdata = self.pc.minmax
        minmax = [["key", "min", "max", "med"]]
        for k, v in minmaxdata.items():
            minmax.append([k] + list(v))
        lines = []
        lines.append(tabulate(minmax, headers="firstrow", tablefmt="psql") + "\n\n")

        self.table.setPlainText("\n".join(lines))
        self.HistDock.setData(self.pc)
        self.BarDock.setData(self.pc)


def mkgui():
    pg.mkQApp("parcoord")
    win = QtWidgets.QMainWindow()
    area = parCoordDockArea()
    win.setCentralWidget(area)
    win.parcoords = area
    return win


# implements: e5
def visualize(dfs, block=True):
    win = mkgui()
    win.parcoords.setParcoordData(dfs)
    win.show()
    if block and not DBG_DONTBLOCK:  # pragma: no cover
        pg.exec()


class FilteredPlots(pg.QtWidgets.QWidget):
    finished = QtCore.Signal()

    def __init__(self, parcoords):
        super().__init__()
        self.la = QtWidgets.QGridLayout()
        self.setLayout(self.la)
        self.plt = pg.GraphicsLayoutWidget()
        self.sel = pg.QtWidgets.QComboBox()
        self.la.addWidget(self.sel)
        self.la.addWidget(self.plt)
        self.la.setSpacing(0)
        self.la.setContentsMargins(0, 0, 0, 0)
        self.pc = parcoords
        self.pc.datachanged.connect(self.createPlots)
        self.pc.selectionchanged.connect(self.updatePlots)
        self.sel.currentTextChanged.connect(self.drawplt)

    def createPlots(self):
        self.dfs = self.pc.dfs
        self.filt = tuple(self.dfs.keys())
        self.sel.clear()

        df0 = self.dfs[self.filt[0]]
        self.sel.addItems(df0.columns)
        self.sel.setCurrentText(df0.columns[0])
        self.drawplt()

    def drawplt(self, _=None):
        df0 = self.dfs[self.filt[0]]
        col = self.sel.currentText()
        xname = df0.index.name
        self.plt.clear()
        self.pltLines = {}
        p1 = self.plt.addPlot()
        p1.addLegend()
        p1.showGrid(1, 1, 0.6)
        p1.setLabel("bottom", xname)
        p1.setLabel("left", col)
        keynos = dict((k, idx) for idx, k in enumerate(self.dfs.keys()))
        for key in self.filt:
            name = f"#{keynos[key]}"
            df = self.dfs[key]
            meta = df.attrs
            pen = self.pc.colormap.map2Col(meta[self.pc.colormapkey])
            self.pltLines[key] = p1.plot(
                x=df.index.values, y=df[col], pen=pen, name=name
            )
        self.finished.emit()
        self.updatePlots()

    def updatePlots(self, filt=None):
        if filt == self.filt:
            return
        if filt is None:
            filt = tuple(self.dfs.keys())
        self.filt = filt
        for k, v in self.pltLines.items():
            vis = k in self.filt
            v.setVisible(vis)
        self.finished.emit()


class ParCoordWidget(QtWebEngineWidgets.QWebEngineView):
    selectionchanged = QtCore.Signal(list)
    datachanged = QtCore.Signal()

    def __init__(self):
        super().__init__()

        self.td = tempfile.TemporaryDirectory()
        self.tempfile = self.td.name + "/tmp.html"
        self.loadFinished.connect(self.onloadFinished)
        self._page = self.page()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.getFilteredKeys)

    def setParcoordData(self, dfs, calculator=None):
        if calculator is not None:
            calculator(dfs)
        meta = getMetaMatrix(dfs)

        # for the parcoords, drop all metadata that is constant
        nu = meta.nunique()
        dropcols = nu[nu == 1].index
        meta = meta.drop(dropcols, axis=1)

        dims = [dict(label=k, values=meta[k]) for k in meta.columns]
        self.meta = meta
        self.dfs = dfs

        csname = "Turbo"
        csvar = meta.columns[0]
        order = np.argsort(dims[0]["values"])
        for idx in range(len(dims)):
            dims[idx]["values"] = dims[idx]["values"][order]

        cs = getattr(pcol.sequential, csname)

        colornumbers = [float(x) for x in dims[0]["values"]]
        line = dict(color=colornumbers, colorscale=csname)
        pc = go.Parcoords(dimensions=dims, line=line)
        fig = go.Figure(data=pc)
        fig.layout.template = "plotly_dark"
        html = fig.to_html()

        open(self.tempfile, "w").write(html)
        url = QtCore.QUrl.fromLocalFile(str(Path(self.tempfile).resolve()))
        self.load(url)

        self.oldfilts = meta.index

        self.calcMinMaxValues()
        csminmax = self.minmax[csvar]
        pos = np.linspace(0, 1, len(cs))
        cm = pg.ColorMap(pos, cs)

        def map2Col(x):
            return cm[((x - csminmax[0]) / csminmax[2])]

        cm.map2Col = map2Col
        self.colormap = cm
        self.colormapkey = csvar

        self.datachanged.emit()

    def calcMinMaxValues(self):
        self.minmax = {}
        for k in self.meta.columns:
            minval = min(self.meta[k])
            maxval = max(self.meta[k])
            self.minmax[k] = (minval, maxval, maxval - minval)

    def getFilteredKeys(self, axlims=None):
        if axlims is None:
            return self.getAxLimits()
        lims = {}
        for k, v in json.loads(axlims).items():
            vs = v.split(",")
            if len(vs) <= 2:
                continue
            minval = float(vs[0])
            maxval = float(vs[-1])
            start = float(vs[1])
            end = start + float(vs[2])
            span = maxval - minval

            startrel = min(1, max(0, start - minval) / span)
            endrel = min(1, max(0, end - minval) / span)
            s, e, sp = self.minmax[k]
            lims[k] = (s + startrel * sp, s + endrel * sp)

        df = self.meta
        for k, (minv, maxv) in lims.items():
            df = df[(df[k] >= minv) & (df[k] <= maxv)]

        filts = df.index
        if not filts.equals(self.oldfilts):
            self.selectionchanged.emit(list(filts.values))
        self.oldfilts = filts

    def getAxLimits(self):

        self._page.runJavaScript(
            """
        var prefixfun = (prefix) =>{if (prefix === 'svg'){
            return 'http://www.w3.org/2000/svg';}else{return null;}};
        (function () {
        res1 = document.evaluate(
        '//svg:line[@stroke-dasharray and @class="highlight"]/@stroke-dasharray',
                document,
                prefixfun,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);

            res2 = document.evaluate(
                '//svg:g[@class="axis-heading"]',
                document,
                prefixfun,
                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,null);

            var dct = {}
            for (let idx=0;idx<res1.snapshotLength;idx++){
                key = res2.snapshotItem(idx).textContent;
                val = res1.snapshotItem(idx).value
                dct[key] = val;
            }

            return JSON.stringify(dct)
            })();""",
            0,
            self.getFilteredKeys,
        )

    def onloadFinished(self, _):
        self.timer.start()
