
import asyncio
import logging
import queue
import json
import re
import threading as thread
from logging.handlers import QueueHandler
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice
from MongoClient import Mongodb

# import services
import bacnet_client.DeviceManagement as dm
import bacnet_client.PointManagement as pm
import bacnet_client.PointPolling as pp


class Bacapp(object):

    __instance = None

    def __init__(self) -> None:
        self.localDevice = LocalBacnetDevice()
        self.app = NormalApplication(self.localDevice.deviceObject,
                                     self.localDevice.deviceAddress)

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


def log(q):
    mongo = Mongodb()
    loop = asyncio.new_event_loop()
    while True:
        try:
            if q.empty() is not True:
                record = q.get()
                m = re.search("\\{.+\\}", str(record))
                mongo_record: dict = json.loads(m.group(0))
                if record is None:
                    loop.close()
                    break
                else:
                    print(m.group(0))
                    coro = mongo.writeDocument(mongo_record,
                                               mongo.getDb(),
                                               "Logs")
                    print(str(coro))

        except Exception as e:
            print(e)


async def main():
    """
    Run or schedule all your services from this entry-point script.
    """

    try:
        bacapp = Bacapp()
        deviceMgr = dm.DeviceManager()
        pointMgr = pm.PointManager()
        pollSrv = pp.PollService()

        devMgr_task = asyncio.create_task(deviceMgr.run(bacapp.app))
        pointMgr_task = asyncio.create_task(pointMgr.run(bacapp.app))
        pollMgr_task = asyncio.create_task(pollSrv.run(bacapp.app))

        await devMgr_task
        await pointMgr_task
        await pollMgr_task
    finally:
        bacapp.app.close()
        devMgr_task.cancel()
        pointMgr_task.cancel()
        pollMgr_task.cancel()
        logger.info("Client application stopping:")

if __name__ == "__main__":

    ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    loop = asyncio.get_event_loop()
    logQ = queue.Queue()
    logProducer = QueueHandler(logQ)
    logProducer.setFormatter(JsonFormatter(datefmt=ISO8601))
    logger = logging.getLogger('ClientLog')
    logger.addHandler(logProducer)
    logger.setLevel(logging.DEBUG)

    try:
        log_consumer_thread = thread.Thread(target=log,
                                            name='log_consumer',
                                            args=(logQ, ),
                                            daemon=True)
        log_consumer_thread.start()
    finally:
        logger.debug("logger thread started")

    asyncio.run(main())
