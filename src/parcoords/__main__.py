try:  # pragma: no cover
    from parcoords.log import setupLogging
    from parcoords.parcoords import main
except ModuleNotFoundError:  # pragma: no cover
    # we need this so the vscode debugger works better
    from parcoords import main
    from log import setupLogging

import sys  # pragma: no cover

setupLogging()  # pragma: no cover
main(sys.argv[1:])  # pragma: no cover
