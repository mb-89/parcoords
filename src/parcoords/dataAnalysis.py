import errno
import itertools as itt
import os
from pathlib import Path

import pandas as pd

from parcoords.exampledata import getExampleData


def getMetaData(store, key):
    md = store.get_storer(key).attrs.metadata
    if store.metasubkey:
        md = md[store.metasubkey]
    return md


def setMetaData(store, key, val):
    s = store.get_storer(key)
    md = getattr(s.attrs, "metadata", {})
    if store.metasubkey:
        md[store.metasubkey][key] = val
    else:
        md[key] = val
    s.attrs.metadata = md


# implements: e1
class ReadContext:
    def __init__(self, path):
        self.path = path
        if str(path) == "#example":
            path = getExampleData()
        if not Path(path).is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        self.h5 = pd.HDFStore(path)

    def __enter__(self):
        data = self.h5.__enter__()
        data.metasubkey = None
        return data

    def __exit__(self, type, value, traceback):
        self.h5.__exit__(type, value, traceback)


# implements: e3
def dumpdict2h5(dct, file):
    with pd.HDFStore(file) as store:
        for key, df in dct.items():
            store.put(key, df)
            store.get_storer(key).attrs.metadata = df.attrs


# implements: e4
def getMetaMatrix(data, subkey=None):

    rows = tuple(data.keys())

    allMetaData = [getMetaData(data, x) for x in rows]

    # shortcut: if we have a key called "meta", we use that
    if all("meta" in x for x in allMetaData):
        subkey = "meta"

    if subkey:
        allMetaData = [x[subkey] for x in allMetaData]
        # in this case, copy all keys of the subkey to the top level , so we can reference
        # them later
    data.metasubkey = subkey

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
