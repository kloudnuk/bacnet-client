
import configparser
import asyncio
import datetime as dt
# import Point as pt
from Device import LocalBacnetDevice
from MongoClient import Mongodb
from bacpypes3.ipv4.app import NormalApplication
from collections import OrderedDict
# from queue import Queue


class PollService(object):
    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    __instance = None

    def __init__(self) -> None:
        self.app: NormalApplication = None
        self.config = configparser.ConfigParser()
        self.point_lists = {}
        self.localDevice = LocalBacnetDevice()
        self.mongo = Mongodb()

    def __new__(cls):
        if PollService.__instance is None:
            PollService.__instance = object.__new__(cls)
        return PollService.__instance

    async def run(self, app):
        if self.app is None:
            self.app = app

        self.config.read("local-device.ini")
        interval = int(self.config.get("point-polling", "interval"))

        await self.poll()
        await asyncio.sleep(interval * 60)

    async def poll(self):
        """
        """
        startTime = dt.datetime.now(tz=self.localDevice.tz) \
                               .strftime(PollService.__ISO8601)
        print(f"INFO - {startTime} - point polling started...")

        for k, v in self.point_lists.items():
            points: OrderedDict = OrderedDict()
            for point in v:
                await point.update()
                # print(f"\npolling {k}")
                # print(f"{point.obj} \
                #       \n{point.spec['value']} \
                #       \n{point.spec['status']} \
                #       \n{point.spec['reliability']} \
                #       \n{point.spec['last synced']}")
                points[str(point.obj)] = point.spec

            await self.mongo \
                .updateFields(self.mongo.getDb(), "Points",
                              {"id": k},
                              {"points": points})

        endTime = dt.datetime.now(tz=self.localDevice.tz) \
                             .strftime(PollService.__ISO8601)
        print(f"INFO - {endTime} - point polling completed...")

    def create_pointList(self, name):
        self.point_lists[name] = []
        return self.point_lists[name] 

    def get_pointList(self, name):
        return self.point_lists.get(name, None)
