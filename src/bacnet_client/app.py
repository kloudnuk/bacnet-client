
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
        devMgr_handle = asyncio.create_task(deviceMgr.run(bacapp.app))
        pointMgr_handle = asyncio.create_task(pointMgr.run(bacapp.app))
        pollMgr_handle = asyncio.create_task(pollSrv.run(bacapp.app))

        await devMgr_handle
        await pointMgr_handle
        await pollMgr_handle
    finally:
        bacapp.app.close()

if __name__ == "__main__":
    asyncio.run(main())
