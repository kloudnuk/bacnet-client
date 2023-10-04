
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
from .SelfManagement import (LocalManager,
                             Subscriber)


class Bacapp(Subscriber):

    __instance = None

    def __init__(self) -> None:
        loadString = "Initializing application manager ..."
        self.localMgr: LocalManager = LocalManager()
        while self.localMgr.initialized is not True:
            progressString = loadString + "."
            print(progressString)
            time.sleep(1)
        self.clients = {
            "mongodb": Mongodb()
        }
        self.service_state: dict = {}
        self.localDevice = LocalBacnetDevice()
        self.app = NormalApplication(self.localDevice.deviceObject,
                                     self.localDevice.deviceAddress)
        self.logger = logging.getLogger('ClientLog')

        if self.localMgr.initialized is True:
            self.localMgr.subscribe(self.__instance)

    def __new__(cls):
        if Bacapp.__instance is None:
            Bacapp.__instance = object.__new__(cls)
        return Bacapp.__instance

    def update(self, section, option, value):
        self.logger.debug("app.update still TODO")


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
    Initialize the application and control services from this entry-point script.
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
        deviceMgr = dm.DeviceManager()
        pointMgr = pm.PointManager()
        pollSrv = pp.PollService()

        # Initialize application task registry.
        app_tasks: dict = {
            "local-device-ini": loop.create_task(bacapp.localMgr.proces_io_deltas()),
            "client-log": loop.create_task(log(logQ, bacapp.clients.get("mongodb"))),
            deviceMgr.settings.get("section"): loop.create_task(deviceMgr.run(bacapp)),
            pointMgr.settings.get("section"): loop.create_task(pointMgr.run(bacapp)),
            pollSrv.settings.get("section"): loop.create_task(pollSrv.run(bacapp))
        }

        # Register task callbacks here.
        app_tasks.get("client-log").add_done_callback(functools.partial(do_log_exit, bacapp))

        for k, v in app_tasks.items():
            bacapp.logger.info(f"{k} service initialized...")
            await v

    finally:
        for k, v in app_tasks.items():
            v.cancel()

if __name__ == "__main__":
    asyncio.run(main())
