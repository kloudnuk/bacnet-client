"""
Bacnet Device Discovery Service entry-point; the service issues who-is
broadcast messages gathereing a list of bacnet devices currently live
on the network along with all the properties they support and a list
of bacnet objects the device is a parent to.
"""

import asyncio
from Device import BacnetDevice, LocalBacnetDevice
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.pdu import Address


async def main():

    # # Define the local bacnet device (the client)
    localDevice = LocalBacnetDevice()

    # Create instance of the bacpype3 application object
    app = NormalApplication(localDevice.deviceObject,
                            localDevice.deviceAddress)
    devices = []
    iams = await app.who_is(0, 4194303, Address("*"))
    iamDict = {iam.iAmDeviceIdentifier: iam.pduSource for iam in iams}

    for id in iamDict:
        try:
            # Get device information
            propList = await app.read_property(
                iamDict[id], id, "propertyList"
            )
            propDict = {str(p): await app.read_property(
                iamDict[id], id, str(p)) for p in propList}
            devices.append(BacnetDevice(id, str(iamDict[id]), propDict))

        except BaseException as be:
            print("ERROR: ", be)
            pass

    for dev in devices:
        print(f"{dev.Id}: {dev.address}")
        for prop in dev.properties:
            print(f"{prop}: {dev.properties[prop]}")
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
