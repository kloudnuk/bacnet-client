
import asyncio
import functools
import logging
import queue
import json
import re
from logging.handlers import QueueHandler
import time
from bacpypes3.ipv4.app import NormalApplication
from .Device import LocalBacnetDevice
from .MongoClient import Mongodb

# import services
import bacnet_client.DeviceManagement as dm
import bacnet_client.PointManagement as pm
import bacnet_client.PointPolling as pp
from .SelfManagement import LocalManager


class Bacapp():

    __instance = None

    def __init__(self) -> None:
        self.loop = None
        loadString = "Initializing application manager ..."
        self.localMgr: LocalManager = LocalManager()
        while self.localMgr.initialized is not True:
            progressString = loadString + "."
            print(progressString)
            time.sleep(1)

        self.localDevice = LocalBacnetDevice()
        self.app = NormalApplication(self.localDevice.deviceObject,
                                     self.localDevice.deviceAddress)
        self.clients = {
            "mongodb": Mongodb()
        }
        self.services = {
            "deviceMgr": dm.DeviceManager(),
            "pointMgr": pm.PointManager(),
            "pollSrv": pp.PollService()
        }
        self.tasks: dict = {}
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if Bacapp.__instance is None:
            Bacapp.__instance = object.__new__(cls)
        return Bacapp.__instance

    async def run(self):
        while True:
            for service, object in self.services.items():
                enable = bool(self.localMgr.read_setting(
                    object.settings.get("section"), "enable"))
                self.logger.debug(f"{service} status: {enable}")
                if enable is True:
                    if service not in self.tasks.keys():
                        self.tasks[service] = self.loop.create_task(object.run(self))
                        self.logger.info(f"Loading {service}")

            for k, v in self.tasks.items():
                if v.done() is True:
                    self.tasks.pop(k)

            await asyncio.sleep(5)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'log': record.name,
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno
        }
        return json.dumps(log_data, ensure_ascii=False)


def do_log_exit(bacapp):
    bacapp.logger.info("Client application stopping:")
    bacapp.logger.info(None)


async def log(q, mongo):
    while True:
        try:
            if q.empty() is not True:
                record = q.get()
                m = re.search("\\{.+\\}", str(record))
                mongo_record: dict = json.loads(m.group(0))

                if record is None:
                    break
                else:
                    print(m.group(0))
                    await mongo.writeDocument(mongo_record,
                                              mongo.getDb(),
                                              "Logs")
        except Exception as e:
            print(e)
        await asyncio.sleep(1)


async def main():
    """
    Entry-point script.
    """
    try:
        # Initialize application services.
        # Logger instances push to a queue, the consumer pulls from the queue every second
        # and sends the logs to MongoDb.
        ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
        loop = asyncio.get_running_loop()
        logQ = queue.Queue()
        logProducer = QueueHandler(logQ)
        logProducer.setFormatter(JsonFormatter(datefmt=ISO8601))
        logger = logging.getLogger('ClientLog')
        logger.addHandler(logProducer)
        logger.setLevel(logging.DEBUG)

        bacapp = Bacapp()
        bacapp.loop = loop

        log_task = loop.create_task(log(logQ, bacapp.clients.get("mongodb")))
        log_task.add_done_callback(functools.partial(do_log_exit, bacapp))
        ini_task = loop.create_task(bacapp.localMgr.proces_io_deltas())
        main_task = loop.create_task(bacapp.run())

        await ini_task
        await log_task
        await main_task

    finally:
        ini_task.cancel()
        log_task.cancel()
        main_task.cancel()
        loop.close()

if __name__ == "__main__":
    asyncio.run(main())
