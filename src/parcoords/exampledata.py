import itertools as itt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

from parcoords import dataAnalysis

DBG_NOCACHE = 0
TMPPATH = "tmp/example.h5"


def getExampleData():  # implements: e2
    global DBG_NOCACHE
    p = Path(TMPPATH)
    if DBG_NOCACHE:
        p.unlink(missing_ok=True)
        DBG_NOCACHE = False
    if p.is_file():
        return p

    p.parent.mkdir(parents=True, exist_ok=True)
    bufferdict = {}
    for key, df in createExampleData():
        bufferdict[key] = df
    dataAnalysis.dumpdict2h5(bufferdict, p)
    return getExampleData()


def createExampleData():
    omegas = np.linspace(1, 10, 10)
    zetas = np.linspace(0, 2, 10)
    params = tuple(itt.product(omegas, zetas))
    L = len(params)

    for idx, (omega, zeta) in enumerate(params):
        print(f"calculating step {idx+1}/{L} for omega={omega}, zeta={zeta}")
        num = [omega ** 2]
        denum = [1, 2 * zeta * omega, omega ** 2]

        tf = signal.TransferFunction(num, denum)
        t, y = tf.step()

        df = pd.DataFrame({"t": t, "y": y})
        df.set_index("t", inplace=True)

        df.attrs["in_omega"] = omega
        df.attrs["in_zeta"] = zeta

        calculateeCharacteristics(df)

        yield f"d{idx}", df


def calculateeCharacteristics(df):
    os = max(0, max(df["y"]) - 1)
    tr = df["y"] > 0.95

    tm = tr & (df["y"] < 1.05)
    inversetm = tm.iloc[::-1]
    lastNotInMargin = inversetm.idxmin()
    if lastNotInMargin == inversetm.index[0]:
        tm = -10
    else:
        tm = lastNotInMargin

    df.attrs["out_os"] = os
    df.attrs["out_tr"] = tr.idxmax()
    df.attrs["out_tm"] = tm
