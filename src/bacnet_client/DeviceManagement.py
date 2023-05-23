
from bacpypes3.ipv4.app import NormalApplication
from Device import LocalBacnetDevice
from bacpypes3.pdu import Address
from MongoClient import Mongodb
from Device import BacnetDevice


class DeviceManager(object):

    """
    Bacnet Device Discovery Service; the service issues who-is
    broadcast messages gathereing a list of bacnet devices currently live
    on the network along with all the properties they support and a list
    of bacnet objects the device is a parent to.
    """

    __instance = None

    def __init__(self) -> None:
        self.devices: set = set()
        self.localDevice = LocalBacnetDevice()
        self.app = NormalApplication(self.localDevice.deviceObject,
                                     self.localDevice.deviceAddress)
        self.lowLimit = 0
        self.highLimit = 4194303
        self.address = Address("*")
        self.mongo = Mongodb()

    def __new__(cls):
        if DeviceManager.__instance is None:
            DeviceManager.__instance = object.__new__(cls)
        return DeviceManager.__instance

    async def discover(self):
        """ Sends a who-is broadcast to the subnet and stores a list of responses. It parses
        through the responses and creates a set of bacnet device definition objects with the 
        corresponding response information.
        """
        print("discovery started...")
        iams = await self.app.who_is(self.lowLimit,
                                     self.highLimit,
                                     self.address)
        iamDict = {iam.iAmDeviceIdentifier: iam.pduSource for iam in iams}
        for id in iamDict:
            try:
                # Get device information
                propList = await self.app.read_property(
                    iamDict[id], id, "propertyList"
                )
                propDict = {str(p): await self.app.read_property(
                    iamDict[id], id, str(p)) for p in propList}
                self.devices.add(BacnetDevice(id, str(iamDict[id]), propDict))
            except BaseException as be:
                print("ERROR: ", be)
                pass
        print("discovery completed...")

    async def commit(self):
        """Check to see if the database collection is empty or has less devices than the in-memory device list.
           1. If the collections is empty just write all devices
           2. if the collection is NOT empty and has the same device count as memory then:
                 2.1 replace all devices.
           3. If the collection is NOT empty and has less devices than in memory device list then:
                 3.1 find the highest device id number in the database
                 3.2 replace all devices with a device id smaller than the id found in step 3.1
                 3.3 write all devices with a device id larger than the id found in step 3.1
        """
        print("commit to database has started...")
        devices = list(self.devices)
        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Devices")
        print(f"Doc Count: {docCount}")
        print(f"Device Count: {len(devices)}")
        if docCount == 0:
            await self.mongo.writeDevices(
                [device.obj for device in devices],
                self.mongo.getDb(),
                "Devices"
            )
        elif docCount == len(devices):
            for device in devices:
                await self.mongo.replaceDevice(device.obj,
                                               self.mongo.getDb(),
                                               "Devices")
        elif docCount < len(devices):
            pass
        elif docCount > len(devices):
            pass
        else:
            pass
        print("commit to database completed...")
        self.devices.clear()
