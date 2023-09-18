
import asyncio
import logging
import datetime as dt
from .Device import LocalBacnetDevice, BacnetDevice
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.apdu import AbortPDU, AbortReason
from .MongoClient import Mongodb


class DeviceManager(object):
    """
    Bacnet Device Discovery Service; the service issues who-is
    broadcast messages gathering a list of bacnet devices currently live
    on the network along with all the properties they support and a list
    of bacnet objects the device is a parent to.
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    __instance = None

    def __init__(self) -> None:
        self.devices: set = set()
        self.localDevice = LocalBacnetDevice()
        self.app = None
        self.lowLimit = 0
        self.highLimit = 4194303
        self.address = Address("*")
        self.mongo = Mongodb()
        self.enable = True
        self.interval = 1440
        self.timeout = 10
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if DeviceManager.__instance is None:
            DeviceManager.__instance = object.__new__(cls)
        return DeviceManager.__instance

    async def run(self, bacapp):
        if self.app is None:
            self.app = bacapp.app
        self.enable = bacapp.read_setting("device-discovery", "enable")

        while self.enable:
            self.interval = bacapp.read_setting("device-discovery", "interval")
            self.timeout = bacapp.read_setting("device-discovery", "timeout")
            await self.discover()
            await self.commit()
            await asyncio.sleep(self.interval * 60)

    async def discover(self):
        """ Sends a who-is broadcast to the subnet and stores a list of responses. It parses
        through the responses and creates a set of bacnet device definition objects with the
        corresponding response information.
        """
        self.logger.info("device discovery started...")

        iams = await self.app.who_is(self.lowLimit,
                                     self.highLimit,
                                     self.address,
                                     self.timeout)
        self.logger.info(f"{len(iams)} BACnet IP devices found...")
        iamDict = {iam.iAmDeviceIdentifier: iam.pduSource for iam in iams}
        for id in iamDict:
            deviceName = await self.app.read_property(iamDict[id], id, "objectName")
            propList = await self.app.read_property(iamDict[id], id, "propertyList")
            propDict = {"device-name": deviceName}
            for prop in propList:
                try:
                    property = await self.app.read_property(iamDict[id], id, str(prop))
                    propDict[str(prop)] = property
                except AbortPDU as e:
                    self.logger.debug(f"{id} - {prop} - {e}")
                    if e.apduAbortRejectReason == AbortReason.segmentationNotSupported:
                        if str(prop) == "object-list":
                            object_list = []
                            list_length = await self.app.read_property(
                                iamDict[id], id, "object-list", array_index=0)
                            for i in range(list_length):
                                object_id: ObjectIdentifier = await self.app.read_property(
                                    iamDict[id], id, "object-list", array_index=i + 1
                                )
                                object_list.append(object_id)

                            propDict["object-list"] = object_list

            device: BacnetDevice = BacnetDevice(id, str(iamDict[id]), propDict)

            endTime = dt.datetime.now(tz=self.localDevice.tz) \
                                 .strftime(DeviceManager.__ISO8601)

            device.spec["last synced"] = endTime
            self.devices.add(device)
        self.logger.info("device discovery completed...")

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
        self.logger.info("device commit to database has started...")
        devices = sorted(list(self.devices))
        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Devices")
        self.logger.debug(f"Doc Count: {docCount}")
        self.logger.info(f"Device Count: {len(devices)}")
        if docCount == 0:
            await self.mongo.writeDocuments(
                [device.spec for device in devices],
                self.mongo.getDb(),
                "Devices"
            )
        elif docCount == len(devices):
            for device in devices:
                await self.mongo.replaceDocument(device.spec,
                                                 self.mongo.getDb(),
                                                 "Devices")

        elif docCount < len(devices):
            dbPayload = await self.mongo.findDocuments(self.mongo.getDb(),
                                                       "Devices",
                                                       query={},
                                                       projection={'id': 1, '_id': 0})

            memDeviceIds = set([int(str(d.deviceId).split(',')[1]) for d in devices])
            dbDeviceIds = set([int(str(d["id"]).split(',')[1]) for d in dbPayload])

            newDeviceIds = memDeviceIds - dbDeviceIds
            foundDeviceIds = memDeviceIds & dbDeviceIds

            self.logger.info(f"devices discovered: {memDeviceIds}")
            self.logger.info(f"devices pulled from db: {dbDeviceIds}")
            self.logger.info(f"new devices to push to db: {newDeviceIds}")
            self.logger.info(f"devices found to update on the db: {foundDeviceIds}")

            newDevices = \
                list(filter(lambda device:
                            int(str(device.deviceId).split(',')[1]) in list(newDeviceIds),
                            sorted(list(self.devices))))
            for nd in newDevices:
                await self.mongo.writeDocument(nd.spec, self.mongo.getDb(), "Devices")

            foundDevices = \
                list(filter(lambda device:
                            int(str(device.deviceId).split(',')[1]) in list(foundDeviceIds),
                            sorted(list(self.devices))))
            for fd in foundDevices:
                await self.mongo.replaceDocument(fd.spec, self.mongo.getDb(), "Devices")

        elif docCount > len(devices):
            dbPayload = await self.mongo.findDocuments(self.mongo.getDb(),
                                                       "Devices",
                                                       query={},
                                                       projection={'id': 1, '_id': 0})

            memDeviceIds = set([int(str(d.deviceId).split(',')[1]) for d in devices])
            dbDeviceIds = set([int(str(d["id"]).split(',')[1]) for d in dbPayload])
            foundDeviceIds = memDeviceIds & dbDeviceIds
            self.logger.info(f"devices discovered: {memDeviceIds}")
            self.logger.info(f"devices pulled from db: {dbDeviceIds}")
            self.logger.info(f"devices found to update on the db: {foundDeviceIds}")
            foundDevices = \
                list(filter(lambda device:
                            int(str(device.deviceId).split(',')[1]) in list(foundDeviceIds),
                            sorted(list(self.devices))))
            for fd in foundDevices:
                await self.mongo.replaceDocument(fd.spec, self.mongo.getDb(), "Devices")
        else:
            self.logger.error("could not commit devices to the database...!", stack_info=True)
            raise Exception("ERROR - could not commit devices to the database...!")

        self.devices.clear()

        self.logger.info("device commit to database completed...")
