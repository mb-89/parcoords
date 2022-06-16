import argparse

from . import __metadata__


def parseArgs(argv):
    p = argparse.ArgumentParser(
        prog="py -m parcoords.py", description=__metadata__.__doc__
    )
    p.add_argument("-?", action="store_true", help="show this help message and exit")
    p.add_argument("-v", "--version", action="store_true", help="prints version")

    args = vars(p.parse_args(argv))
    return args, p


def main(argv=None):
    if argv is None:
        argv = ["-?"]
    args, parser = parseArgs(argv)
    if args["version"]:
        print(__metadata__.__version__)
        return 0
    if args["?"]:
        parser.print_help()
        return 0

    from parcoords import api

    return 0
