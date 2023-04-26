"""
Bacnet Device type definition with methods to encode/decode to and from json,
and a factory method to create BacnetDevice DTOs.
"""

import json
import configparser
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import IPv4Address


class BacnetDeviceDto(object):
    def __init__(self, properties: dict) -> None:
        for property in properties:
            setattr(self, property, properties[property])


class BacnetDevice():
    def __init__(
            self, id, addr: str, props: dict) -> None:
        self.deviceId = id
        self.address: str = addr
        self.properties: dict = props
        self.obj: dict = {"id": str(self.deviceId),
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

    def toDto(self):
        return BacnetDeviceDto(self.obj)


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

        print(f"""
            id: {LocalBacnetDevice.__objId}
            address: {LocalBacnetDevice.__localAddress}
            name: {LocalBacnetDevice.__objName}
            max apdu: {LocalBacnetDevice.__maxApduLength}
            segmentation: {LocalBacnetDevice.__segmentation}
            max segments: {LocalBacnetDevice.__maxSegments}
            vendor id: {LocalBacnetDevice.__vendorId}
            """)

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
