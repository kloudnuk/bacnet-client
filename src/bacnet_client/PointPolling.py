
import configparser
import asyncio
import datetime as dt
from Device import LocalBacnetDevice
from MongoClient import Mongodb
from bacpypes3.ipv4.app import NormalApplication
from queue import Queue


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
        self.queues = {}
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
        # await self.update()
        await asyncio.sleep(interval * 60)

    async def poll(self):
        """
        """
        startTime = dt.datetime.now(tz=self.localDevice.tz) \
                               .strftime(PollService.__ISO8601)
        print(f"INFO - {startTime} - start polling...")

        for k, v in self.queues.items():
            print(f"polling queue: {k}")
            while not v.empty():
                print((v.get()).spec["name"])

        endTime = dt.datetime.now(tz=self.localDevice.tz) \
                             .strftime(PollService.__ISO8601)
        print(f"INFO - {endTime} - polling done...")

    async def update(self):
        print("TODO")

    def create_queue(self, name):
        new_queue = Queue()
        self.queues[name] = new_queue
        return new_queue

    def get_queue(self, name):
        return self.queues.get(name, None)
