
import sys
import json
import pytz
# import traceback
import configparser
from collections import OrderedDict
from bacpypes3.pdu import IPv4Address
from bacpypes3.local.device import DeviceObject
from bacpypes3.basetypes import Segmentation


class BacnetDevice():

    """
    Bacnet Device  normalizes all bacnet library methods used to data suited to be exported to a database.
    It overrides a number of methods to allow for easy string conversion, serialization, sorting and merging values
    from a previous state.
    """

    def __init__(
            self, id, addr: str, props: dict, doNormalize=True) -> None:
        if doNormalize:
            self.__properties = OrderedDict(
                sorted(OrderedDict({p: self.normalize(str(p), props[p]) for p in props}).items(),
                       key=lambda x: x[0])
            )
        else:
            self.__properties = OrderedDict(
                sorted(OrderedDict(props).items(), key=lambda x: x[0]))

        self.spec = OrderedDict({"id": str(id),
                                 "address": addr,
                                 "last synced": None,
                                 "properties": self.__properties})

    @property
    def deviceId(self):
        return self.spec["id"]

    @property
    def name(self):
        return self.spec["device-name"]

    @property
    def address(self):
        return self.spec["address"]

    @property
    def lastSynced(self):
        return self.spec["last synced"]

    @property
    def properties(self):
        return self.spec["properties"]

    def __str__(self) -> str:
        return json.dumps(self.spec)

    def __bytes__(self) -> bytes:
        databytes = str(self.spec).encode('utf-8')
        datalen = len(databytes).to_bytes(2, byteorder='big')
        return datalen + databytes

    def __dir__(self) -> dict:
        return list(self.spec.keys())

    def __hash__(self):
        return hash((self.deviceId, self.address))

    def __add__(self, other) -> None:
        if type(other) == BacnetDevice:
            for p in self.spec:
                self.spec[p] = other.obj[p]
        else:
            raise Exception("Cannot merge (+) with a type other than BacnetDevice")

    def __eq__(self, other) -> bool:
        if type(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) == int(str(other.deviceId).split(",")[1]) and \
                str(self.address) == str(other.address)
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __ne__(self, other) -> bool:
        if type(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) != int(str(other.deviceId).split(",")[1]) and \
                str(self.address) != str(other.address)
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __lt__(self, other) -> bool:
        if type(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) < int(str(other.deviceId).split(",")[1])
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __gt__(self, other) -> bool:
        if type(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) > int(str(other.deviceId).split(",")[1])
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    @classmethod
    def oct2uuid(self, octetString):
        octets = str(octetString)[1:][:-1].split('\\')
        uuid = ""
        for octet in octets:
            try:
                uuid += str(int(octet[1:], 16))
            except:  # noqa: E722
                uuid += str(octet[1:])
        return uuid

    @classmethod
    def oct2Address(self, octetString):
        octets = str(octetString)[:-1].split('\\')
        ipString: str = ""
        if len(octets) <= 1:
            ipString = None
        elif len(octets) == 2:
            ipString = str(int(octets[1][1:], 16))
        elif len(octets) == 7:
            ipString = \
                f"{int(octets[1][1:], 16)}.{int(octets[2][1:], 16)}.{int(octets[3][1:], 16)}.{int(octets[4][1:], 16)}:{int(octets[5][1:] + octets[6][1:], 16)}"  # noqa: E501

        else:
            ipString = octetString
        return ipString

    def normalize(self, property, value):
        try:
            normalized: dict = {"value": "",
                                "type": str(type(value))[8:-2]}
            if property == "restart-notification-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}\n", "utf-8"))

            elif property == "time-of-device-restart":
                normalized["value"] = str(
                    f"{value.dateTime.date} {value.dateTime.time}")
                return normalized

            elif property == "object-list":
                normalized["value"] = [str(v) for v in value]
                sorted(normalized["value"])
                return normalized

            elif property == "utc-time-synchronization-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}\n", "utf-8"))

            elif property == "protocol-object-types-supported":
                normalized["value"] = str(value).split(";")
                sorted(normalized["value"])
                return normalized

            elif property == "protocol-services-supported":
                normalized["value"] == str(value).split(";")
                sorted(normalized["value"])
                return normalized

            elif property == "time-synchronization-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}\n", "utf-8"))

            elif property == "align-intervals":
                normalized["value"] == "True" if 1 else "False"
                return normalized

            elif property == "daylight-savings-status":
                normalized["value"] == "True" if 1 else "False"
                return normalized

            elif property == "last-restore-time":
                normalized["value"] = str(
                    f"{value.dateTime.date} {value.dateTime.time}")
                return normalized
            elif property == "device-uuid":
                normalized["value"] = self.oct2uuid(value)
                return normalized
            elif property == "active-cov-subscriptions":
                try:
                    normalized["value"] = \
                        [{"device":
                          self.oct2Address(v.recipient
                                            .recipient
                                            .address
                                            .macAddress),
                          "propertyReference":
                            f"{v.monitoredPropertyReference.objectIdentifier}-{v.monitoredPropertyReference.propertyIdentifier}",  # noqa: E501
                          "timeRemaining": str(v.timeRemaining),
                          "covIncrement": str(v.covIncrement)} for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}\n", "utf-8"))

            else:
                normalized["value"] = str(value)
                return normalized
        except:  # noqa: E722
            return "not-supported"


class LocalBacnetDevice:

    """
    The client does not need to expose any services nor listen for network requests so it only implements
    properties as needed. There should only be one local device per application so it is Singleton.
    """

    __instance = None

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read('local-device.ini')
        self.objId = self.config.get("device", "objectIdentifier")
        self.objName = self.config.get("device", "objectName")
        self.maxApduLength = self.config.get("network", "maxApduLengthAccepted")
        self.segmentation = Segmentation.segmentedBoth
        self.maxSegments = self.config.get("network", "maxSegmentsAccepted")
        self.vendorId = self.config.get("device", "vendorIdentifier")
        self.localAddress = self.config.get("network", "interface")
        self.tz = pytz.timezone(self.config.get("device", "tz"))

    def __new__(cls):
        if LocalBacnetDevice.__instance is None:
            LocalBacnetDevice.__instance = object.__new__(cls)
        return LocalBacnetDevice.__instance

    def __str__(self) -> str:
        return f"""
            id: {self.objId}
            address: {self.localAddress}
            name: {self.objName}
            max apdu: {self.maxApduLength}
            segmentation: {str(self.segmentation)}
            max segments: {self.maxSegments}
            vendor id: {self.vendorId}
            timezone: {self.tz}
            """

    @property
    def deviceObject(self):
        return DeviceObject(
            objectIdentifier=("device", self.objId),
            objectName=self.objName,
            maxApduLengthAccepted=self.maxApduLength,
            segmentationSupported=self.segmentation,
            maxSegmentsAccepted=self.maxSegments,
            vendorIdentifier=self.vendorId
        )

    @property
    def deviceAddress(self):
        return IPv4Address(self.localAddress)
