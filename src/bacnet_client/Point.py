import datetime as dt
import logging
from collections import OrderedDict
from .Device import LocalBacnetDevice
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier, StatusFlags, Reliability
from bacpypes3.ipv4.app import NormalApplication


class BacnetPoint:
    """
    The base class for bacnet point objects of 3 diferent kinds, analog, binary, and multi-state.
    The constructor receives the point's corresponding edge from the object-graph, it then knows
    how to build its own properties by making native bacnet calls. The point object can also
    fetch its own value updates from the network.
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"

    def __init__(
        self, app: NormalApplication, localDevice: LocalBacnetDevice, edge, obj
    ) -> None:
        self.spec: OrderedDict = OrderedDict()
        self.app: NormalApplication = app
        self.localDevice: LocalBacnetDevice = localDevice
        self.device: dict = edge
        self.obj = obj
        self.logger = logging.getLogger("ClientLog")

    async def build(self):
        try:
            name = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.objectName,
            )

            value = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.presentValue,
            )

            status: StatusFlags = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.statusFlags,
            )

            reliability: Reliability = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.reliability,
            )

            description = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.description,
            )
            self.spec.clear()
            self.spec.update(
                {
                    "id": self.obj,
                    "device": [self.device["name"], self.device["id"]],
                    "name": name,
                    "value": value,
                    "status": str(status),
                    "reliability": str(reliability),
                    "description": str(description),
                    "last synced": dt.datetime.now(
                        tz=self.localDevice.settings.get("tz")
                    ).strftime(BacnetPoint.__ISO8601),
                }
            )
        except:
            self.logger.error(f"failed to build point object {self.obj}")
            raise;

    async def update(self):
        try:
            value = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.presentValue,
            )

            status: StatusFlags = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.statusFlags,
            )

            reliability: Reliability = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.reliability,
            )
            self.spec["value"] = value
            self.spec["status"] = str(status)
            self.spec["reliability"] = str(reliability)
            self.spec["last synced"] = dt.datetime.now(
                tz=self.localDevice.settings.get("tz")
            ).strftime(BacnetPoint.__ISO8601)
        except:
            self.logger.error(
                f"{dt.datetime.now(tz=self.localDevice.settings.get('tz'))} - \
                  {self.obj}"
            )


class AnalogPoint(BacnetPoint):
    """ """

    async def build(self):
        try:
            await super().build()
            units = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.units,
            )

            maxVal = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.maxPresValue,
            )

            minVal = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.minPresValue,
            )
            self.spec["units"] = str(units)
            self.spec["maxVal"] = maxVal
            self.spec["minVal"] = minVal
        except:
            errorTime = dt.datetime.now(
                tz=self.localDevice.settings.get("tz")
            ).strftime(super().__ISO8601)
            self.logger.error(
                f"ERROR - {errorTime} - \
                    Could not read all data for analog point - {self.obj}"
            )


class BinaryPoint(BacnetPoint):
    """ """

    async def build(self):
        try:
            await super().build()
            active_text = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.activeText,
            )

            inactive_text = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.inactiveText,
            )

            elapsed_active = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.elapsedActiveTime,
            )
            self.spec["active-text"] = active_text
            self.spec["inactive-text"] = inactive_text
            self.spec["elapsed-active-time"] = elapsed_active

        except:
            errorTime = dt.datetime.now(
                tz=self.localDevice.settings.get("tz")
            ).strftime(super().__ISO8601)
            self.logger.error(
                f"{errorTime} - \
                    Could not read all data for analog point - {self.obj}"
            )


class MsvPoint(BacnetPoint):
    """ " """

    async def build(self):
        try:
            await super().build()
            state_count = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.numberOfStates,
            )

            state_text = await self.app.read_property(
                Address(self.device["address"]),
                ObjectIdentifier(self.obj),
                PropertyIdentifier.stateText,
            )
            self.spec["state-count"] = state_count
            self.spec["state-labels"] = state_text

        except:
            errorTime = dt.datetime.now(
                tz=self.localDevice.settings.get("tz")
            ).strftime(super().__ISO8601)
            self.logger.error(
                f"{errorTime} - \
                    Could not read all data for analog point - {self.obj}"
            )
