
import configparser
import pickle
import logging
import asyncio
from collections import OrderedDict
from .Device import LocalBacnetDevice
from .MongoClient import Mongodb
import bacnet_client.Point as pt
import bacnet_client.PointPolling as pp
from bacpypes3.ipv4.app import NormalApplication


class PointManager(object):
    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __og_fp = '../res/object-graph.pkl'
    __instance = None

    def __init__(self) -> None:
        self.app: NormalApplication = None
        self.poller: pp.PollService = None
        self.config = configparser.ConfigParser()
        self.deviceSpecs = []
        self.object_graph = {}
        self.localDevice = LocalBacnetDevice()
        self.lowLimit = 0
        self.highLimit = 4194303
        self.mongo = Mongodb()
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if PointManager.__instance is None:
            PointManager.__instance = object.__new__(cls)
        return PointManager.__instance

    async def run(self, app):
        if self.app is None:
            self.app = app

        self.config.read("../res/local-device.ini")
        interval = int(self.config.get("point-discovery", "interval"))
        enable = bool(self.config.get("point-discovery", "enable"))

        while enable:
            await self.discover()
            await self.commit()
            self.config.read("../res/local-device.ini")
            interval = int(self.config.get("point-discovery", "interval"))
            enable = bool(self.config.get("point-discovery", "enable"))
            await asyncio.sleep(interval * 60)

    async def discover(self):
        """
        Discovers listed bacnet devices objects filtering for points, trends, alarms, and schedules.
        It then creates instance objects process them and sends output data specs to the database.
        """

        self.logger.info("point discovery started...")
        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Devices")
        if docCount > 0:
            dbPayload = await self.mongo.findDocuments(self.mongo.getDb(),
                                                       "Devices",
                                                       query={},
                                                       projection={'id': 1,
                                                                   'address': 1,
                                                                   'properties': 1,
                                                                   '_id': 0})

            try:
                with open(PointManager.__og_fp, 'wb') as object_graph:
                    object_graph.flush()
            except:  # noqa: E722
                self.logger.critical("ERROR Unable to persist object graph to file...!")

            for device in dbPayload:
                try:
                    deviceSpec = OrderedDict({"name": device["properties"]["device-name"]["value"],
                                              "id": device["id"],
                                              "address": device["address"],
                                              "points": OrderedDict()
                                              })
                    pointList = deviceSpec["points"]
                    objListValue = device["properties"]["object-list"]["value"]

                    # TODO - Add trend, schedule, and alarm objects to the object graph here.
                    #        All object types filtered into 'objList' will be parsed into the
                    #         object-graph for secondary services to derive data from.
                    objList = list(filter(lambda kind: 'analog-value' in kind
                                          or 'analog-input' in kind
                                          or 'analog-output' in kind
                                          or 'binary-value' in kind
                                          or 'binary-input' in kind
                                          or 'binary-output' in kind
                                          or 'multi-state-value' in kind
                                          or 'multi-state-input' in kind
                                          or 'multi-state-output' in kind, objListValue))

                    self.object_graph[device["id"]] = {}

                    for i, obj in enumerate(objList):
                        self.object_graph[device["id"]][obj] = {"id": deviceSpec["id"],
                                                                "name": deviceSpec["name"],
                                                                "address": deviceSpec["address"],
                                                                "point": obj}
                        if "analog" in str(obj):
                            point = pt.AnalogPoint(self.app, self.localDevice, self.object_graph[device["id"]][obj],
                                                   obj)
                            await point.build()
                            pointList[str(point.obj)] = point.spec
                        elif "binary" in str(obj):
                            point = pt.BinaryPoint(self.app, self.localDevice, self.object_graph[device["id"]][obj],
                                                   obj)
                            await point.build()
                            pointList[str(point.obj)] = point.spec
                        elif "multi-state" in str(obj):
                            point = pt.MsvPoint(self.app, self.localDevice, self.object_graph[device["id"]][obj],
                                                obj)
                            await point.build()
                            pointList[str(point.obj)] = point.spec
                        else:
                            point = pt.BacnetPoint(self.app, self.localDevice, self.object_graph[device["id"]][obj],
                                                   obj)
                            await point.build()
                            pointList[str(point.obj)] = point.spec

                    with open(PointManager.__og_fp, 'wb') as object_graph:
                        try:
                            pickle.dump(self.object_graph, object_graph)
                        except:  # noqa: E722
                            self.logger.critical("ERROR Unable to append {deviceSpec['id']} object graph to file...!")

                except:  # noqa: E722
                    self.logger.critical(f"ERROR object-list is not available in \
                            {device['properties']['device-name']['value']}")
                    continue

                self.deviceSpecs.append(deviceSpec)

        self.logger.info("point discovery completed...")

    async def commit(self):

        self.logger.info("points commit to database has started...")

        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Points")
        self.logger.info(f"doc count: {docCount}")
        self.logger.info(f"point lists to database: {len(list(self.deviceSpecs))}")

        if docCount == 0:
            await self.mongo.writeDocuments(
                self.deviceSpecs,
                self.mongo.getDb(),
                "Points"
            )
        elif docCount == len(self.deviceSpecs):
            for spec in self.deviceSpecs:
                await self.mongo.replaceDocument(
                    spec,
                    self.mongo.getDb(),
                    "Points")
        else:
            self.logger.error(f"ERROR - 1. ({docCount} > {len(self.deviceSpecs)}) -> add/replace \n\
                  2. ({docCount} < {len(self.deviceSpecs)}) -> replace/no-sync")

        self.deviceSpecs.clear()
        self.object_graph.clear()

        self.logger.info("point commit completed...")
