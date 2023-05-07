"""
Bacnet Device type definition with methods to encode/decode to and from json,
and a factory method to create BacnetDevice DTOs.
"""

import json
import configparser
import sys
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import IPv4Address
# from bacpypes3.basetypes import ObjectIdentifier


class BacnetDeviceDto(object):
    def __init__(self, properties: dict) -> None:
        for property in properties:
            setattr(self, property, properties[property])


class BacnetDevice():
    def __init__(
            self, id, addr: str, props: dict) -> None:
        self.Id = id
        self.address: str = addr
        self.properties: dict = {p:
                                 self.normalize(str(p),
                                                props[p]) for p in props}
        self.obj: dict = {"id": str(self.Id),
                          "address": self.address,
                          "properties": self.properties}

    def __str__(self) -> str:
        return json.dumps(str(self.obj))

    def __bytes__(self) -> bytes:
        databytes = str(self.obj).encode('utf-8')
        datalen = len(databytes).to_bytes(2, byteorder='big')
        return datalen + databytes

    def __dir__(self):
        return list(self.obj.keys()) + \
            list(self.properties.keys())

    @classmethod
    def oct2uuid(self, octetString):
        octets = str(octetString)[1:][:-1].split('\\')
        uuid = ""
        for octet in octets:
            try:
                uuid += str(int(octet[1:], 16))
            except:
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

    def toDto(self):
        return BacnetDeviceDto(self.obj)

    def normalize(self, property, value):
        try:
            normalized: dict = {"value": "",
                                "type": str(type(value))}
            if property == "restart-notification-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}", "utf-8"))

            elif property == "time-of-device-restart":
                normalized["value"] = str(
                    f"{value.dateTime.date} {value.dateTime.time}")
                return normalized

            elif property == "object-list":
                normalized["value"] = [str(v) for v in value]
                return normalized

            elif property == "utc-time-synchronization-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}", "utf-8"))

            elif property == "protocol-object-types-supported":
                normalized["value"] = str(value).split(";")
                return normalized

            elif property == "protocol-services-supported":
                normalized["value"] == str(value).split(";")
                return normalized

            elif property == "time-synchronization-recipients":
                try:
                    normalized["value"] = \
                        [{"device": str(v.device),
                          "address": self.oct2Address(v.address.macAddress)}
                            for v in value]
                    return normalized
                except Exception as e:
                    sys.stderr.buffer.write(bytes(f"{property}: {e}", "utf-8"))

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
                    sys.stderr.buffer.write(bytes(f"{property}: {e}", "utf-8"))

            else:
                normalized["value"] = str(value)
                return normalized
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}", "utf-8"))
            return ""


class LocalBacnetDevice:
    __instance = None
    __config = configparser.ConfigParser()
    __objId = None
    __objName = None
    __maxApduLength = None
    __segmentation = None
    __maxSegments = None
    __vendorId = None
    __vendorId = None

    def __init__(self) -> None:
        LocalBacnetDevice.__config.read('local-device.ini')
        LocalBacnetDevice.__objId = LocalBacnetDevice.__config.get(
            "device", "objectIdentifier")
        LocalBacnetDevice.__objName = LocalBacnetDevice.__config.get(
            "device", "objectName")
        LocalBacnetDevice.__maxApduLength = LocalBacnetDevice.__config.get(
            "network", "maxApduLengthAccepted")
        LocalBacnetDevice.__segmentation = LocalBacnetDevice.__config.get(
            "network", "segmentationSupported")
        LocalBacnetDevice.__maxSegments = LocalBacnetDevice.__config.get(
            "network", "maxSegmentsAccepted")
        LocalBacnetDevice.__vendorId = LocalBacnetDevice.__config.get(
            "device", "vendorIdentifier")
        LocalBacnetDevice.__localAddress = \
            LocalBacnetDevice.__config.get("network", "interface")

    def __str__(self) -> str:
        return f"""
            id: {LocalBacnetDevice.__objId}
            address: {LocalBacnetDevice.__localAddress}
            name: {LocalBacnetDevice.__objName}
            max apdu: {LocalBacnetDevice.__maxApduLength}
            segmentation: {LocalBacnetDevice.__segmentation}
            max segments: {LocalBacnetDevice.__maxSegments}
            vendor id: {LocalBacnetDevice.__vendorId}
            """

    @classmethod
    @property
    def deviceObject(cls):
        return DeviceObject(
            objectIdentifier=("device", LocalBacnetDevice.__objId),
            objectName=LocalBacnetDevice.__objName,
            maxApduLengthAccepted=LocalBacnetDevice.__maxApduLength,
            segmentationSupported=LocalBacnetDevice.__segmentation,
            maxSegmentsAccepted=LocalBacnetDevice.__maxSegments,
            vendorIdentifier=LocalBacnetDevice.__vendorId,
        )

    @classmethod
    @property
    def deviceAddress(cls):
        return IPv4Address("wlp112s0")

    def __new__(cls):
        if LocalBacnetDevice.__instance is None:
            LocalBacnetDevice.__instance = object.__new__(cls)
        return LocalBacnetDevice.__instance
