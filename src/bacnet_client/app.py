
import asyncio
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice

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


async def main():
    """
    Run or schedule all your services from this entry-point script.
    """
    bacapp = Bacapp()
    deviceMgr = dm.DeviceManager()
    pointMgr = pm.PointManager()
    pollSrv = pp.PollService()

    try:
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
    asyncio.run(main())
