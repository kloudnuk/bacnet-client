
import asyncio
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice

# import services
import bacnet_client.DeviceManagement as dm
import bacnet_client.PointManagement as pm


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

    try:
        while True:
            # Run services
            output = await asyncio.gather(
                dm.DeviceManager().run(bacapp.app),
                pm.PointManager().run_discover(bacapp.app)
            )
            print(output)
            await asyncio.sleep(1)
    finally:
        bacapp.app.close()

if __name__ == "__main__":
    asyncio.run(main())
