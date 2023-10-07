
import sys
import json
import pytz
import logging
import time
from collections import OrderedDict
from bacpypes3.pdu import IPv4Address
from bacpypes3.local.device import DeviceObject
from bacpypes3.basetypes import Segmentation
from .SelfManagement import (LocalManager,
                             Subscriber)


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
        if isinstance(other) == BacnetDevice:
            for p in self.spec:
                self.spec[p] = other.obj[p]
        else:
            raise Exception("Cannot merge (+) with a type other than BacnetDevice")

    def __eq__(self, other) -> bool:
        if isinstance(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) == int(str(other.deviceId).split(",")[1]) and \
                str(self.address) == str(other.address)
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __ne__(self, other) -> bool:
        if isinstance(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) != int(str(other.deviceId).split(",")[1]) and \
                str(self.address) != str(other.address)
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __lt__(self, other) -> bool:
        if isinstance(other) == BacnetDevice:
            return int(str(self.deviceId).split(",")[1]) < int(str(other.deviceId).split(",")[1])
        else:
            raise Exception("Cannot compare with a type other than BacnetDevice")

    def __gt__(self, other) -> bool:
        if isinstance(other) == BacnetDevice:
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
                                "type": str(type(value))[18:-2]}
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


class LocalBacnetDevice(Subscriber):

    """
    The client does not need to expose any services nor listen for network requests so it only implements
    properties as needed. There should only be one local device per application so it is Singleton.
    """

    __instance = None
    __ini_sections = ('device', 'network')

    def __init__(self) -> None:
        self.segmentation = Segmentation.segmentedBoth
        loadString = "Initializing application manager ..."
        self.localMgr: LocalManager = LocalManager()
        while self.localMgr.initialized is not True:
            progressString = loadString + "."
            print(progressString)
            time.sleep(1)
        self.settings: dict = {
            "section": LocalBacnetDevice.__ini_sections,
            "objectIdentifier": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[0],
                                                           "objectIdentifier"),
            "objectName": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[0],
                                                     "objectName"),
            "vendorIdentifier": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[0],
                                                           "vendorIdentifier"),
            "tz": pytz.timezone(self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[0],
                                                           "tz")),
            "maxApduLengthAccepted": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[1],
                                                                "maxApduLengthAccepted"),
            "maxSegmentsAccepted": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[1],
                                                              "maxSegmentsAccepted"),
            "interface": self.localMgr.read_setting(LocalBacnetDevice.__ini_sections[1],
                                                    "interface")
        }
        self.logger = logging.getLogger('ClientLog')

        if self.localMgr.initialized is True:
            self.localMgr.subscribe(self.__instance)

    def __new__(cls):
        if LocalBacnetDevice.__instance is None:
            LocalBacnetDevice.__instance = object.__new__(cls)
        return LocalBacnetDevice.__instance

    def update(self, section, option, value):
        if section in self.settings.get("section")[0]:
            oldvalue = self.settings.get(option)
            self.settings[option] = pytz.timezone(value)
            self.logger.debug(f"{section} > {option} updated from \
                              {oldvalue} to {self.settings.get(option)}")
        elif section in self.settings.get("section")[1]:
            oldvalue = self.settings.get(option)
            self.settings[option] = value
            self.logger.debug(f"{section} > {option} updated from \
                              {oldvalue} to {self.settings.get(option)}")

    def __str__(self) -> str:
        return f"""
            id: {self.settings.get("objectIdentifier")}
            address: {self.settings.get("interface")}
            name: {self.settings.get("objectName")}
            max apdu: {self.settings.get("maxApduLengthAccepted")}
            segmentation: {str(self.segmentation)}
            max segments: {self.settings.get("maxSegmentsAccepted")}
            vendor id: {self.settings.get("vendorIdentifier")}
            timezone: {self.settings.get("tz")}
            """

    @property
    def deviceObject(self):
        return DeviceObject(
            objectIdentifier=("device", self.settings.get("objectIdentifier")),
            objectName=self.settings.get("objectName"),
            maxApduLengthAccepted=self.settings.get("maxApduLengthAccepted"),
            segmentationSupported=self.segmentation,
            maxSegmentsAccepted=self.settings.get("maxSegmentsAccepted"),
            vendorIdentifier=self.settings.get("vendorIdentifier")
        )

    @property
    def deviceAddress(self):
        return IPv4Address(self.settings.get("interface"))
