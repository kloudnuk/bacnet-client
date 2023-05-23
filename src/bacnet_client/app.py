
import asyncio
import time
# import services
import bacnet_client.DeviceManagement as dm


async def main():

    """
    Run or schedule all your services from this entry-point script.
    """

    devmgr = dm.DeviceManager()

    await devmgr.discover()
    await devmgr.commit()
    
    print("1st discovery and commit complete")
    time.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
