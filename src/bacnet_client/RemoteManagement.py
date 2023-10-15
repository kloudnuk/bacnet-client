
import logging
import json
import traceback
import asyncio
from collections import (OrderedDict, deque)
from .MongoClient import Mongodb
from abc import ABC, abstractmethod
from .SelfManagement import (LocalManager,
                             ServiceScheduler)


class Composite(ABC):
    @abstractmethod
    def update(self):
        pass


class Section(Composite):
    """
    """

    def __init__(self, name, localMgr) -> None:
        self.name = name
        self.tree = {self.name: {}}
        self.localMgr = localMgr

    def __str__(self) -> str:
        return json.dumps(self.tree, ensure_ascii=False)

    def update(self):
        for name in self.localMgr.config.options(self.name):
            value = self.localMgr.config.get(self.name, name)
            self.tree[self.name] |= {name: value}


class Configuration(Composite):
    """
    """

    def __init__(self, localMgr) -> None:
        self.name = "local-device.ini"
        self.localMgr = localMgr
        self.sections = [Section]
        self.options = []

    def __str__(self) -> str:
        return json.dumps(self.get(), ensure_ascii=False)

    def get(self):
        output = OrderedDict()
        for section in self.sections:
            output.update(section.tree)
        return output

    def update(self):
        self.sections.clear()
        self.localMgr.config.read(f"{self.localMgr.respath}{self.name}")
        for section in self.localMgr.config.sections():
            s = Section(section, self.localMgr)
            s.update()
            self.sections.append(s)
        return self


class EventManager():
    """"
    """
    __instance = None

    def __init__(self) -> None:
        self.store = deque()
        self.localMgr = None
        self.localConfig = None
        self.logger = logging.getLogger("ClientLog")

    def __new__(cls):
        if EventManager.__instance is None:
            EventManager.__instance = object.__new__(cls)
        return EventManager.__instance

    async def ingest(self, event):
        try:
            self.store.append(event)
        except Exception as e:
            self.logger.error(f"error {e} trying to record a \
                              remote configuration change event {event}")
        asyncio.get_running_loop().call_soon(self.process)

    def process(self):
        while len(self.store) > 0:
            try:
                event = self.store.pop()
                update: dict = event['updateDescription']['updatedFields']
                self.logger.debug(f"update-fields: {update}")
                for k, v in update.items():
                    section = k.split(".")[0]
                    option = k.split(".")[1]
                    self.localConfig[section][option] = v
                    self.localMgr.config.set(section, option, v)
                with open(f"{self.localMgr.respath}local-device.ini", 'w') as configFile:
                    self.localMgr.config.write(configFile)
            except Exception as e:
                self.logger.error({e})
                traceback.print_exc()


class ScheduledUpdateManager():
    """
    This service has an initialization sequence that only runs during application bootup.
    During bootup it checks that there is a document with its nuk_id
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    __instance = None

    def __init__(self) -> None:
        self.app = None
        self.localMgr: LocalManager = None
        self.mongo: Mongodb = None
        self.configuration = None
        self.eventMgr = None
        self.scheduler: ServiceScheduler = ServiceScheduler()
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if ScheduledUpdateManager.__instance is None:
            ScheduledUpdateManager.__instance = object.__new__(cls)
        return ScheduledUpdateManager.__instance

    async def run(self, bacapp):
        if self.app is None:
            self.app = bacapp.app
        if self.mongo is None:
            self.mongo = bacapp.clients.get("mongodb")

        if bacapp.localMgr.initialized is True:
            if self.localMgr is None:
                self.localMgr = bacapp.localMgr

                self.configuration = Configuration(self.localMgr)
                localConfig = self.configuration.update().get()
                self.eventMgr = EventManager()
                self.eventMgr.localMgr = self.localMgr
                self.eventMgr.localConfig = localConfig
                nukid = localConfig['device']['nukid']
                pipeline = [{'$match': {'operationType': 'update'}}]

                remoteConfig = await self.mongo.findDocument(self.mongo.getDb(),
                                                             "Configuration",
                                                             {"device.nukid": nukid})
                self.logger.debug(f"remote configuration: {remoteConfig}")

                if remoteConfig is None:
                    await self.mongo.writeDocument(localConfig,
                                                   self.mongo.getDb(),
                                                   "Configuration")
                    await self.mongo.watch_collection(self.mongo.getDb(),
                                                      "Configuration",
                                                      pipeline,
                                                      self.eventMgr)
                else:
                    await self.mongo.watch_collection(self.mongo.getDb(),
                                                      "Configuration",
                                                      pipeline,
                                                      self.eventMgr)
