
import sys
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
        self.points: OrderedDict = OrderedDict()
        self.localDevice = LocalBacnetDevice()
        self.lowLimit = 0
        self.highLimit = 4194303
        self.mongo = Mongodb()

    def __new__(cls):
        if PointManager.__instance is None:
            PointManager.__instance = object.__new__(cls)
        return PointManager.__instance

    async def discover(self, app: NormalApplication):
        docCount = await self.mongo.getDocumentCount(self.mongo.getDb(),
                                                     "Devices")
        if docCount > 0:
            dbPayload = await self.mongo.findDevices(self.mongo.getDb(),
                                                     "Devices",
                                                     query={},
                                                     projection={'id': 1,
                                                                 'address': 1,
                                                                 'properties': 1,
                                                                 '_id': 0})

            for device in dbPayload:
                try:
                    deviceSpec = {"name": device["properties"]["device-name"]["value"],
                                  "id": device["id"],
                                  "address": device["address"],
                                  "points": {}
                                  }
                    for obj in device["properties"]["object-list"]["value"]:

                        pointName = await app.read_property(Address(device["address"]),
                                                            ObjectIdentifier(obj),
                                                            PropertyIdentifier.objectName)

                        try:
                            pointValue = await app.read_property(Address(device["address"]),
                                                                 ObjectIdentifier(obj),
                                                                 PropertyIdentifier.presentValue)
                        except:  # noqa: E722
                            sys.stderr.buffer.write(bytes(f"ERROR {device['id']} - {obj}\n", "utf-8"))
                            continue

                        try:
                            pointStatus: StatusFlags = await app.read_property(Address(device["address"]),
                                                                               ObjectIdentifier(obj),
                                                                               PropertyIdentifier.statusFlags)
                        except:  # noqa: E722
                            sys.stderr.buffer.write(bytes(f"ERROR {device['id']} - {obj}\n", "utf-8"))
                            continue

                        pointSpec = {"id": obj,
                                     "value": round(pointValue, 4),
                                     "status": str(pointStatus)}
                        deviceSpec["points"][pointName] = pointSpec

                    print(deviceSpec)
                except:  # noqa: E722
                    continue
