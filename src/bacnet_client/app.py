
import asyncio
import logging
import queue
import threading as thread
from logging.handlers import QueueHandler
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice
# from MongoClient import Mongodb

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


def log(q):
    # mongo = Mongodb()
    while True:
        try:
            if q.empty() is not True:
                record = q.get()
                if record is None:
                    break
                else:
                    # TODO - send logs to mongo db's own logging collection (one per database) - FORMAT PROPERLY
                    print(record)
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

if __name__ == "__main__":

    ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    logQ = queue.Queue()
    logProducer = QueueHandler(logQ)
    logFormat = (logging.Formatter(datefmt=ISO8601,
                                   fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logProducer.setFormatter(logFormat)
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
