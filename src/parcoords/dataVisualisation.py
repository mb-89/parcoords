import importlib
import json
import tempfile
from pathlib import Path

import numpy as np
import plotly.colors as pcol
import plotly.graph_objects as go
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtCore, QtWidgets

from parcoords.dataAnalysis import getMetaData, getMetaMatrix

QtWebEngineWidgets = importlib.import_module(pg.Qt.lib + ".QtWebEngineWidgets")
DBG_DONTBLOCK = False


class parCoordDockArea(DockArea):
    def __init__(self):
        super().__init__()
        self.pc = pc = ParCoordWidget()
        pcd = Dock("metadata")
        pcd.addWidget(pc)

        pd = Dock("plots")
        self.plts = plts = FilteredPlots(self.pc)
        pd.addWidget(plts)

        self.addDock(pcd, "top")
        self.addDock(pd, "bottom")

    def setParcoordData(self, dfs):
        self.pc.setParcoordData(dfs)


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


class FilteredPlots(pg.GraphicsLayoutWidget):
    finished = QtCore.Signal()

    def __init__(self, parcoords):
        super().__init__()
        self.pc = parcoords
        self.pc.datachanged.connect(self.createPlots)
        self.pc.selectionchanged.connect(self.updatePlots)

    def createPlots(self):
        self.dfs = self.pc.dfs
        self.filt = self.dfs.keys()

        self.clear()
        self.pltLines = {}
        p1 = self.addPlot()
        p1.addLegend()
        p1.showGrid(1, 1, 0.6)
        p1.setLabel("bottom", "t/s")
        p1.setLabel("left", "y")
        for key in self.filt:
            df = self.dfs[key]
            meta = getMetaData(self.dfs, key)
            pen = self.pc.colormap.map2Col(meta[self.pc.colormapkey])
            self.pltLines[key] = p1.plot(
                x=df.index.values, y=df["y"], pen=pen, name=key
            )
        self.finished.emit()

    def updatePlots(self, filt=None):
        if filt == self.filt:
            return
        if filt is None:
            filt = self.dfs.keys()
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

    def setParcoordData(self, dfs):
        meta = getMetaMatrix(dfs)
        dims = [dict(label=k, values=meta[k]) for k in meta.columns]
        self.meta = meta
        self.dfs = dfs

        csname = "Turbo"
        csvar = meta.columns[0]
        cs = getattr(pcol.sequential, csname)

        line = dict(color=meta[csvar], colorscale=csname)
        pc = go.Parcoords(dimensions=dims, line=line)
        fig = go.Figure(data=pc)
        fig.layout.template = "plotly_dark"
        html = fig.to_html()

        open(self.tempfile, "w").write(html)
        url = QtCore.QUrl.fromLocalFile(Path(self.tempfile).resolve())
        self.load(url)

        self.oldfilts = meta.index

        self.calcMinMaxValues()
        csminmax = self.minmax[csvar]
        pos = np.linspace(0, 1, len(cs))
        cm = pg.ColorMap(pos, cs)
        cm.map2Col = lambda x: cm[((x - csminmax[0]) / csminmax[2])]
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
