from parcoords import dataAnalysis, dataVisualisation
from parcoords import log as logging

log = logging.getLogger()

read = dataAnalysis.ReadContext


def show(data):
    dataVisualisation.visualize(data)
