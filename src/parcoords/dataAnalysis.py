import errno
import itertools as itt
import os
from pathlib import Path

import pandas as pd

from parcoords.exampledata import getExampleData


# implements: e1
def read(path):
    path = Path(path)
    if str(path) == "#example":
        path = getExampleData()
    if not Path(path).is_file():
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

    dct = h52dict(path)
    doCalculations(dct)
    return dct


calcCallbacks = []


def addCalcCallback(cb):
    global calcCallbacks
    calcCallbacks.append(cb)


def doCalculations(dfs):
    for cb in calcCallbacks:
        try:
            cb(dfs)
        except:  # noqa: E722
            pass


# implements: e3
def dict2h5(dct, file):
    with pd.HDFStore(file) as store:
        for key, df in dct.items():
            store.put(key, df)
            store.get_storer(key).attrs.metadata = df.attrs


def h52dict(file, subsample=1):
    dct = {}
    with pd.HDFStore(file) as store:
        keys = list(store.keys()[::subsample])
        L = len(keys)
        for idx, key in enumerate(keys):
            if idx % 100 == 0:
                print(f"loading key {idx+1}/{L}")
            df = store[key]
            if df.empty:
                continue
            dct[key] = df
            dct[key].attrs = store.get_storer(key).attrs.metadata
    return dct


# implements: e4
def getMetaMatrix(data, subkey=None):
    rows = tuple(data.keys())
    allMetaData = [data[x].attrs for x in rows]
    cfi = itt.chain.from_iterable

    def isUsableMetaKey(key):
        try:
            metadata = set(x.get(key, None) for x in allMetaData)
            metadata.discard(None)
            sorted(float(x) for x in metadata)
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
