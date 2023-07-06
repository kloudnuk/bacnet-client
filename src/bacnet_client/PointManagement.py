
import traceback
import configparser
import asyncio
from collections import OrderedDict
from Device import LocalBacnetDevice
from MongoClient import Mongodb
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier, StatusFlags


class PointManager(object):
    """
    Bacnet Point Discovery Service: the service issues who-has messages and creates
    a collection of points on the database for each device already on the database.
    """

    __instance = None

    def __init__(self) -> None:
        self.app: NormalApplication = None
        self.config = configparser.ConfigParser()
        self.points = []
        self.localDevice = LocalBacnetDevice()
        self.lowLimit = 0
        self.highLimit = 4194303
        self.mongo = Mongodb()

    def __new__(cls):
        if PointManager.__instance is None:
            PointManager.__instance = object.__new__(cls)
        return PointManager.__instance

    async def run_discover(self, app):
        if self.app is None:
            self.app = app

        self.config.read("local-device.ini")
        interval = int(self.config.get("device-discovery", "interval"))

        await self.discover()
        await asyncio.sleep(interval * 60)

    async def getPointSpec(self, obj, device):

        pointName = await self.app.read_property(Address(device["address"]),
                                                 ObjectIdentifier(obj),
                                                 PropertyIdentifier.objectName)
        pointValue = 0
        pointStatus = None
        pointUnits = None
        try:
            pointValue = await self.app.read_property(Address(device["address"]),
                                                      ObjectIdentifier(obj),
                                                      PropertyIdentifier.presentValue)
        except:  # noqa: E722
            pass

        try:
            pointStatus: StatusFlags = await self.app.read_property(Address(device["address"]),
                                                                    ObjectIdentifier(obj),
                                                                    PropertyIdentifier.statusFlags)
        except:  # noqa: E722
            pass

        try:
            pointUnits = await self.app.read_property(Address(device["address"]),
                                                      ObjectIdentifier(obj),
                                                      PropertyIdentifier.units)
        except:  # noqa: E722
            pass

        pointSpec = OrderedDict({"id": obj,
                                 "name": pointName,
                                 "value": round(pointValue, 4),
                                 "status": str(pointStatus),
                                 "units": str(pointUnits)})
        return pointSpec

    async def getDeviceSpec(self, device):
        deviceSpec = OrderedDict({"name": device["properties"]["device-name"]["value"],
                                  "id": device["id"],
                                  "address": device["address"],
                                  "points": OrderedDict()
                                  })
        objListValue = device["properties"]["object-list"]["value"]
        objListType = device["properties"]["object-list"]["type"]

        if objListType == "bacpypes3.constructeddata.ArrayOfObjectIdentifier":
            objList = list(filter(lambda kind: 'analog-value' in kind
                                  or 'analog-input' in kind
                                  or 'analog-output' in kind
                                  or 'binary-value' in kind
                                  or 'binary-input' in kind
                                  or 'binary-output' in kind
                                  or 'multi-state-value' in kind
                                  or 'multi-state-input' in kind
                                  or 'multi-state-output' in kind, objListValue))

            for i, obj in enumerate(objList):
                points: OrderedDict = deviceSpec["points"]
                points[i] = await self.getPointSpec(obj, device)
        else:
            raise ValueError(f"ERROR object-list is not available in {device}...")

        print(deviceSpec)
        return deviceSpec

    async def discover(self):
        """
        """
        print("discovery started...")
        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Devices")
        if docCount > 0:
            dbPayload = await self.mongo.findDocuments(self.mongo.getDb(),
                                                       "Devices",
                                                       query={},
                                                       projection={'id': 1,
                                                                   'address': 1,
                                                                   'properties': 1,
                                                                   '_id': 0})
            for device in dbPayload:
                try:
                    self.points.append(await self.getDeviceSpec(device))
                except:  # noqa: E722
                    traceback.print_exc()
                    continue

    async def commit(self, context):
        print("TODO")
