
from collections import OrderedDict
from Device import LocalBacnetDevice


class PointManager(object):

    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __instance = None

    def __init__(self, bacapp) -> None:
        self.points: OrderedDict = OrderedDict()
        self.localDevice = LocalBacnetDevice()
        self.app = bacapp

    def __new__(cls):
        if PointManager.__instance is None:
            PointManager.__instance = object.__new__(cls)
        return PointManager.__instance
