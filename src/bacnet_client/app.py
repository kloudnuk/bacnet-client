
import asyncio

# import services
import bacnet_client.DeviceManagement as dm


async def main():

    """
    Run or schedule all your services from this entry-point script.
    """

    # Declare service instances
    devmgr = dm.DeviceManager()

    # Run services
    await devmgr.run(3)


if __name__ == "__main__":
    asyncio.run(main())
