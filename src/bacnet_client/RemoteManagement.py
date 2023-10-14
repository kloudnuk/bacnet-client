
import logging
import json
from collections import (OrderedDict, deque)
from .MongoClient import Mongodb
from abc import ABC, abstractmethod
from .SelfManagement import (LocalManager,
                             ServiceScheduler)


class EventManager():
    """"
    """
    __instance = None

    def __init__(self) -> None:
        self.store = deque()
        self.logger = logging.getLogger("ClientLog")

    def __new__(cls):
        if EventManager.__instance is None:
            EventManager.__instance = object.__new__(cls)
        return EventManager.__instance

    def ingest(self, event):
        try:
            self.store.append(event)
        except Exception as e:
            self.logger.error(f"error {e} trying to record a \
                              remote configuration change event {event}")
        return self

    def process(self):
        pass
        return self


class ScheduledUpdateManager():
    """
    TODO - This service has an initialization sequence that only runs during application bootup.
    During bootup it checks that there is a document with its nuk_id
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    __instance = None

    def __init__(self) -> None:
        self.app = None
        self.localMgr: LocalManager = None
        self.mongo: Mongodb = None
        self.configuration = None
        self.scheduler: ServiceScheduler = ServiceScheduler()
        self.eventMgr = EventManager()
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


class Composite(ABC):

    @abstractmethod
    def update(self):
        pass


class Section(Composite):
    def __init__(self, name, localMgr) -> None:
        self.name = name
        self.tree = {self.name: {}}
        self.localMgr = localMgr

    def update(self):
        for name in self.localMgr.config.options(self.name):
            value = self.localMgr.config.get(self.name, name)
            self.tree[self.name] |= {name: value}


class Configuration(Composite):
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
