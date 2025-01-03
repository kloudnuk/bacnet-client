import pickle
import logging
from collections import OrderedDict
from .Device import LocalBacnetDevice
from .SelfManagement import LocalManager, Subscriber, ServiceScheduler
import bacnet_client.Point as pt
import bacnet_client.PointPolling as pp
from bacpypes3.ipv4.app import NormalApplication


class PointManager(Subscriber):
    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __instance = None
    __isBootup = True

    def __init__(self) -> None:
        self.app: NormalApplication = None
        self.poller: pp.PollService = None
        self.localMgr: LocalManager = None
        self.og_fp = None
        self.mongo = None
        self.scheduler: ServiceScheduler = ServiceScheduler()
        self.deviceSpecs = []
        self.object_graph = {}
        self.localDevice = LocalBacnetDevice()
        self.lowLimit = 0
        self.highLimit = 4194303
        self.settings: dict = {
            "section": "point-discovery",
            "enable": None,
            "interval": None,
        }
        self.subscribed = False
        self.logger = logging.getLogger("ClientLog")

    def __new__(cls):
        if PointManager.__instance is None:
            PointManager.__instance = object.__new__(cls)
        return PointManager.__instance

    def update(self, section, option, value):
        if section in self.settings.get("section"):
            oldvalue = self.settings.get(option)
            self.settings[option] = value
            self.logger.debug(
                f"{section} > {option} updated from {oldvalue} to {self.settings.get(option)}"
            )

    async def run(self, bacapp):
        if self.app is None:
            self.app = bacapp.app
        if self.mongo is None:
            self.mongo = bacapp.clients.get("mongodb")

        if bacapp.localMgr.initialized is True:
            if self.localMgr is None:
                self.localMgr = bacapp.localMgr
            if self.subscribed is False:
                bacapp.localMgr.subscribe(self.__instance)
                self.subscribed = True

            self.og_fp = self.localMgr.respath + "object-graph.pkl"

            self.settings["enable"] = self.localMgr.read_setting(
                self.settings.get("section"), "enable"
            )
            self.settings["interval"] = self.localMgr.read_setting(
                self.settings.get("section"), "interval"
            )

            if (
                self.scheduler.check_ticket(
                    self.settings.get("section"), interval=self.settings.get("interval")
                )
                or self.__isBootup
            ):
                await self.discover()
                await self.commit()
                self.__isBootup = False

    async def discover(self):
        """
        Discovers listed bacnet devices objects filtering for points, trends, alarms, and schedules.
        It then creates instance objects process them and sends output data specs to the database.
        """

        self.logger.info("point discovery started...")
        try:
            docCount = await self.mongo.getDocumentCount(self.mongo.getDb(), "Devices")
        except:
            self.logger.error("Could not get a device doc count...")
        else:
            if docCount > 0:
                dbPayload = await self.mongo.findDocuments(
                    self.mongo.getDb(),
                    "Devices",
                    query={},
                    projection={"id": 1, "address": 1, "properties": 1, "_id": 0},
                )

                try:
                    with open(self.og_fp, "wb") as object_graph:
                        object_graph.flush()
                except:  # noqa: E722
                    self.logger.critical("ERROR Unable to persist object graph to file...!")

                for device in dbPayload:
                    try:
                        deviceSpec = OrderedDict(
                            {
                                "name": device["properties"]["device-name"]["value"],
                                "id": device["id"],
                                "address": device["address"],
                                "points": OrderedDict(),
                            }
                        )
                        pointList = deviceSpec["points"]
                        objListValue = device["properties"]["object-list"]["value"]

                        # TODO - Add trend, schedule, and alarm objects to the object graph here.
                        #        All object types filtered into 'objList' will be parsed into the
                        #         object-graph for secondary services to derive data from.
                        objList = list(
                            filter(
                                lambda kind: "analog-value" in kind
                                or "analog-input" in kind  # noqa: W503
                                or "analog-output" in kind  # noqa: W503
                                or "binary-value" in kind  # noqa: W503
                                or "binary-input" in kind  # noqa: W503
                                or "binary-output" in kind  # noqa: W503
                                or "multi-state-value" in kind  # noqa: W503
                                or "multi-state-input" in kind  # noqa: W503
                                or "multi-state-output" in kind,
                                objListValue,  # noqa: W503
                            )
                        )

                        self.object_graph[device["id"]] = {}

                        for i, obj in enumerate(objList):
                            self.object_graph[device["id"]][obj] = {
                                "id": deviceSpec["id"],
                                "name": deviceSpec["name"],
                                "address": deviceSpec["address"],
                                "point": obj,
                            }
                            if "analog" in str(obj):
                                point = pt.AnalogPoint(
                                    self.app,
                                    self.localDevice,
                                    self.object_graph[device["id"]][obj],
                                    obj,
                                )
                                await point.build()
                                pointList[str(point.obj)] = point.spec
                            elif "binary" in str(obj):
                                point = pt.BinaryPoint(
                                    self.app,
                                    self.localDevice,
                                    self.object_graph[device["id"]][obj],
                                    obj,
                                )
                                await point.build()
                                pointList[str(point.obj)] = point.spec
                            elif "multi-state" in str(obj):
                                point = pt.MsvPoint(
                                    self.app,
                                    self.localDevice,
                                    self.object_graph[device["id"]][obj],
                                    obj,
                                )
                                await point.build()
                                pointList[str(point.obj)] = point.spec
                            else:
                                point = pt.BacnetPoint(
                                    self.app,
                                    self.localDevice,
                                    self.object_graph[device["id"]][obj],
                                    obj,
                                )
                                await point.build()
                                pointList[str(point.obj)] = point.spec

                        with open(self.og_fp, "wb") as object_graph:
                            try:
                                pickle.dump(self.object_graph, object_graph)
                            except:  # noqa: E722
                                self.logger.critical(
                                    f"ERROR Unable to append {deviceSpec['id']} object graph to file...!"
                                )

                    except:  # noqa: E722
                        self.logger.critical(
                            f"ERROR object-list is not available in \
                                {device['properties']['device-name']['value']}"
                        )

                    self.deviceSpecs.append(deviceSpec)

        self.logger.info("point discovery completed...")

    async def commit(self):

        self.logger.info("points commit to database has started...")

        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(), "Points")
        self.logger.info(f"doc count: {docCount}")
        self.logger.info(f"point lists to database: {len(list(self.deviceSpecs))}")

        if docCount == 0:
            await self.mongo.writeDocuments(
                self.deviceSpecs, self.mongo.getDb(), "Points"
            )
            self.logger.debug(f"Document count {docCount}")
        elif docCount == len(self.deviceSpecs):
            self.logger.debug(
                f"Documents ({docCount}) == Specs: {len(self.deviceSpecs)}"
            )
            for spec in self.deviceSpecs:
                await self.mongo.replaceDocument(spec, self.mongo.getDb(), "Points")
        elif docCount < len(self.deviceSpecs):
            self.logger.debug(
                f"Documents ({docCount}) < Specs: {len(self.deviceSpecs)}"
            )
            dbPayload = await self.mongo.findDocuments(
                self.mongo.getDb(), "Points", query={}, projection={"id": 1, "_id": 0}
            )
            memSpecIds = set(
                [int(str(spec["id"]).split(",")[1]) for spec in self.deviceSpecs]
            )
            dbSpecIds = set([int(str(spec["id"]).split(",")[1]) for spec in dbPayload])

            self.logger.debug(f"device specs available in memory {memSpecIds}")
            self.logger.debug(f"device specs pulled from db {dbSpecIds}")
            newSpecIds = memSpecIds - dbSpecIds
            foundSpecIds = memSpecIds & dbSpecIds

            self.logger.debug(f"device specs available in memory: {memSpecIds}")
            self.logger.debug(f"device specs pulled from db: {dbSpecIds}")
            self.logger.debug(f"new specs to push to db: {newSpecIds}")
            self.logger.debug(f"existing specs to be updated on db: {foundSpecIds}")

            newSpecs = list(
                filter(
                    lambda spec: int(str(spec["id"]).split(",")[1]) in list(newSpecIds),
                    sorted(list(self.deviceSpecs)),
                )
            )
            for ns in newSpecs:
                await self.mongo.writeDocument(ns, self.mongo.getDb(), "Points")

            foundSpecs = list(
                filter(
                    lambda spec: int(str(spec["id"]).split(",")[1])
                    in list(foundSpecIds),
                    sorted(list(self.deviceSpecs)),
                )
            )
            for fs in foundSpecs:
                await self.mongo.replaceDocument(fs, self.mongo.getDb(), "Points")

        elif docCount > len(self.deviceSpecs):
            self.logger.debug(
                f"Documents ({docCount}) > Specs: {len(self.deviceSpecs)}"
            )
            dbPayload = await self.mongo.findDocuments(
                self.mongo.getDb(), "Points", query={}, projection={"id": 1, "_id": 0}
            )
            memSpecIds = set(
                [int(str(spec["id"]).split(",")[1]) for spec in self.deviceSpecs]
            )
            dbSpecIds = set([int(str(spec["id"]).split(",")[1]) for spec in dbPayload])
            foundSpecIds = memSpecIds & dbSpecIds

            self.logger.debug(f"device specs available in memory: {memSpecIds}")
            self.logger.debug(f"device specs pulled from db: {dbSpecIds}")
            self.logger.debug(f"existing specs to be updated on db: {foundSpecIds}")

            foundSpecs = list(
                filter(
                    lambda spec: int(str(spec["id"]).split(",")[1])
                    in list(foundSpecIds),
                    sorted(list(self.deviceSpecs)),
                )
            )
            for fs in foundSpecs:
                await self.mongo.replaceDocument(fs, self.mongo.getDb(), "Points")

        else:
            self.logger.error(
                "could not commit devices to the database...!", stack_info=True
            )

        self.deviceSpecs.clear()
        self.object_graph.clear()

        self.logger.info("point commit completed...")
