
import asyncio

# import services
import bacnet_client.DeviceManagement as dm


async def main():

    """
    Run or schedule all your services from this entry-point script.
    """

    devmgr = dm.DeviceManager()

    await devmgr.discover()
    [print(dev) for dev in devmgr.devices]


if __name__ == "__main__":
    asyncio.run(main())
