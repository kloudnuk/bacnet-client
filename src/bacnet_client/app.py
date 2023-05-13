# App dependencies only
"""
Run or schedule all your services from this entry-point script.
"""
# Import Local Application and Device dependencies
import asyncio
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice

# import services
import DeviceDiscovery


async def main():
    localDevice = LocalBacnetDevice()
    
    app = NormalApplication(localDevice.deviceObject,
                            localDevice.deviceAddress)

    await DeviceDiscovery.run(app)

if __name__ == "__main__":
    asyncio.run(main())
