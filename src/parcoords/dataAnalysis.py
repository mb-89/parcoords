import itertools as itt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

DBG_NOCACHE = 0


def getMetaData(store, key):
    return store.get_storer(key).attrs.metadata


class ReadContext:
    def __init__(self, path):
        self.path = path
        if str(path) == "#example":
            path = getExampleData()
        self.h5 = pd.HDFStore(path)

    def __enter__(self):
        return self.h5.__enter__()

    def __exit__(self, type, value, traceback):
        try:
            self.h5.__exit__(type, value, traceback)
        except:  # noqa: E722
            pass


def getExampleData():
    global DBG_NOCACHE
    p = Path("tmp/example.h5")
    if DBG_NOCACHE:
        p.unlink(missing_ok=True)
        DBG_NOCACHE = False
    if p.is_file():
        return p

    p.parent.mkdir(parents=True, exist_ok=True)

    with pd.HDFStore(p) as store:
        for key, df in createExampleData():
            store.put(key, df)
            store.get_storer(key).attrs.metadata = df.attrs

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

        df.attrs["omega"] = omega
        df.attrs["zeta"] = zeta

        calculateCharacteristics(df)

        yield f"d{idx}", df


def calculateCharacteristics(df):
    os = max(0, max(df["y"]) - 1)
    tr = df["y"] > 0.95

    tm = tr & (df["y"] < 1.05)
    inversetm = tm.iloc[::-1]
    lastNotInMargin = inversetm.idxmin()
    if lastNotInMargin == inversetm.index[0]:
        tm = -10
    else:
        tm = lastNotInMargin

    df.attrs["os"] = os
    df.attrs["tr"] = tr.idxmax()
    df.attrs["tm"] = tm


def getMetaMatrix(data):

    rows = tuple(data.keys())
    allMetaData = [getMetaData(data, x) for x in rows]

    cfi = itt.chain.from_iterable

    def isUsableMetaKey(key):
        try:
            metadata = set(x.get(key, None) for x in allMetaData)
            metadata.discard(None)
            sorted(metadata)
        except:  # noqa: E722 # if set() or sorted() fail, assume the data is unusable
            return False
        return True

    metaKeys = set(cfi(x.keys() for x in allMetaData))
    metaKeys = (x for x in metaKeys if not x.startswith("_"))
    metaKeys = sorted(x for x in metaKeys if isUsableMetaKey(x))

    lst = [
        [key] + [allMetaData[idx][y] for y in metaKeys] for idx, key in enumerate(rows)
    ]
    df = pd.DataFrame(lst)
    df.columns = ["key"] + metaKeys
    df.set_index("key", inplace=True)

    return df
