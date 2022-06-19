import pytest
from pyqtgraph.Qt import QtWidgets

from parcoords import api, dataVisualisation, exampledata, log
from parcoords import parcoords as module

exampledata.DBG_NOCACHE = True
dataVisualisation.DBG_DONTBLOCK = True


def test_visualizeExamples(tmpdir, qtbot):
    exampledata.TMPPATH = str(tmpdir / "tmp.h5")

    # proofs: c1, e1, f1, e2, f2, e3
    with api.read("#example") as data:

        # add some uniusable metadata for coverage
        md = data.get_storer("/d0").attrs.metadata
        md["unusable"] = {"bla": 1, "blubb": [2, 3]}
        data.get_storer("/d0").attrs.metadata = md

        # proofs: c2, e5, f3, f4, e4
        win = dataVisualisation.mkgui()
        win.parcoords.setParcoordData(data)
        qtbot.addWidget(win)
        win.show()

        # wait for initial setup
        qtbot.waitSignal(win.parcoords.plts.finished, timeout=10000)
        win.parcoords.plts.filt = ["/d0"]
        win.parcoords.pc.onloadFinished(0)
        win.parcoords.pc.getFilteredKeys()
        win.parcoords.pc.getFilteredKeys('{"in_omega": "0.25,0.75,0.5"}')
        win.parcoords.plts.updatePlots(None)
        win.parcoords.plts.updatePlots(win.parcoords.plts.filt)
        win.parcoords.pc.getFilteredKeys('{"in_omega": "0,1"}')


def test_edgecases(monkeypatch):
    with pytest.raises(FileNotFoundError):
        module.main(["-src", "#doesntExist"])
    log.setupLogging()  # to trigger the edge-case of already initialized logger

    with monkeypatch.context() as mp:

        def noop(*args, **kwargs):
            pass

        mp.setattr(QtWidgets.QMainWindow, "show", noop)
        mp.setattr(dataVisualisation.parCoordDockArea, "setParcoordData", noop)
        module.main(["-src", "#example"])
