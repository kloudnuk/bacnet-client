
import asyncio
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


class Bacapp(object):

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
        self.localDevice = LocalBacnetDevice()
        self.app = NormalApplication(self.localDevice.deviceObject,
                                     self.localDevice.deviceAddress)
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if Bacapp.__instance is None:
            Bacapp.__instance = object.__new__(cls)
        return Bacapp.__instance


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
    Run or schedule all your services from this entry-point script.
    """
    try:
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
        bacapp.logger.debug(f"LOCAL DEVICE : {bacapp.localDevice}")

        io_delta_task = loop.create_task(bacapp.localMgr.proces_io_deltas())
        devMgr_task = loop.create_task(deviceMgr.run(bacapp))
        pointMgr_task = loop.create_task(pointMgr.run(bacapp))
        pollMgr_task = loop.create_task(pollSrv.run(bacapp))
        logger_task = loop.create_task(log(logQ, bacapp.clients.get("mongodb")))

        await io_delta_task
        await devMgr_task
        await pointMgr_task
        await pollMgr_task
        await logger_task

    finally:
        io_delta_task.cancel()
        bacapp.app.close()
        devMgr_task.cancel()
        pointMgr_task.cancel()
        pollMgr_task.cancel()
        logger.info("Client application stopping:")
        logger.info(None)
        logger_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
