
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
        self.devices = set()
        self.committed = []
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

    async def commit(self):
        # Compare (or populate if empty) committed list of devices, to
        # to discovered set of devices. Use BacnetDevice class add operator to 
        # merge new individual field changes and the eq operator to know if there
        # properties that have changed.
        if self.committed.count() == 0:
            devices = list(self.devices)
            self.committed = devices
            await self.mongo.writeDevices(
                [device.obj for device in self.committed],
                self.mongo.getDb(),
                "Devices"
            )
        else:
            for i, device in enumerate(devices):
                if device != self.committed[i]:
                    self.committed + device
                    self.mongo.replaceDevice(device,
                                             self.committed[i],
                                             self.mongo.getDb(),
                                             "Devices")
        self.devices.clear()
