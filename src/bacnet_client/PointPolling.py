
import asyncio
import logging
import pickle
from .Device import LocalBacnetDevice
from .Point import BacnetPoint
from .MongoClient import Mongodb
from .SelfManagement import LocalManager
from bacpypes3.ipv4.app import NormalApplication
from collections import OrderedDict


class PollService(object):
    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __instance = None

    def __init__(self) -> None:
        self.localMgr: LocalManager = LocalManager()
        self.app: NormalApplication = None
        self.localDevice = LocalBacnetDevice()
        self.mongo = Mongodb()
        self.object_graph: dict = {}
        self.poll_lists = OrderedDict()
        self.points_specs = OrderedDict()
        self.logger = logging.getLogger('ClientLog')
        self.interval = 15
        self.enable = False

    def __new__(cls):
        if PollService.__instance is None:
            PollService.__instance = object.__new__(cls)
        return PollService.__instance

    async def run(self, bacapp):
        if self.app is None:
            self.app = bacapp.app
        self.enable = self.localMgr.read_setting("point-polling", "enable")

        while self.enable:
            self.interval = self.localMgr.read_setting("point-polling", "interval")
            self.enable = self.localMgr.read_setting("point-polling", "enable")
            await self.poll()
            await asyncio.sleep(self.interval * 60)

    async def poll(self):
        """
        The point polling manager relies on the point manager to build an object graph
        of device-point relationships which gets serialized into a pickle file. The
        polling service parses the object graph and loads point object updates to the mongo
        database on a user defined time interval
        """
        self.logger.info("point polling started...")

        await self.load_pointLists()

        for k, v in self.object_graph.items():
            self.logger.debug(f"\ncommitting poll to db {k}")
            await self.mongo \
                .updateFields(self.mongo.getDb(), "Points",
                              {"id": k},
                              {"points": self.points_specs[k]})
        self.logger.info("point polling completed...")

    async def load_pointLists(self):
        try:
            with open('../res/object-graph.pkl', 'rb') as object_graph:
                self.object_graph: dict = pickle.load(object_graph)
            for k, v in self.object_graph.items():
                self.logger.info(f"\npolling {k}")
                self.poll_lists[k] = []
                self.points_specs[k] = OrderedDict()

                for key, value in self.object_graph[k].items():
                    self.logger.debug(key)
                    point: BacnetPoint = BacnetPoint(self.app,
                                                     self.localDevice,
                                                     value,
                                                     value["point"])
                    await point.update()

                    self.poll_lists[k].append(point)
                    self.points_specs[k][point.obj] = point.spec

        except:  # noqa: E722
            self.logger.critical("ERROR Unable to retrieve object graph from file OR poll or commit poll...!")
