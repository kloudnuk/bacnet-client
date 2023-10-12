
import logging
import json
from collections import OrderedDict
from .MongoClient import Mongodb
from abc import ABC, abstractmethod
from .SelfManagement import (LocalManager,
                             Subscriber,
                             ServiceScheduler)


class ScheduledUpdateManager(Subscriber):
    """
    TODO - This service has an initialization sequence that only runs during application bootup.
    During bootup it checks that there is a document with its nuk_id
    """

    __ISO8601 = "%Y-%m-%dT%H:%M:%S%z"
    __instance = None
    __ini_section = "device"

    def __init__(self) -> None:
        self.app = None
        self.localMgr: LocalManager = None
        self.mongo: Mongodb = None
        self.configuration = None
        self.scheduler: ServiceScheduler = ServiceScheduler()
        self.settings = {
            "section": ScheduledUpdateManager.__ini_section,
            "enable": None,
            "interval": None
        }
        self.subscribed = False
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if ScheduledUpdateManager.__instance is None:
            ScheduledUpdateManager.__instance = object.__new__(cls)
        return ScheduledUpdateManager.__instance

    def update(self, section, option, value):
        if section in self.settings.get("section"):
            oldvalue = self.settings.get(option)
            self.settings[option] = value
            self.logger.debug(f"{section} > {option} updated from \
                              {oldvalue} to {self.settings.get(option)}")

    async def run(self, bacapp):
        if self.app is None:
            self.app = bacapp.app
        if self.mongo is None:
            self.mongo = bacapp.clients.get("mongodb")

        if bacapp.localMgr.initialized is True:
            if self.localMgr is None:
                self.localMgr = bacapp.localMgr
            if self.subscribed is False:
                bacapp.localMgr.subscribe(self.__instance)
                self.subscribed = True

        self.settings['enable'] = self.localMgr.read_setting(self.settings.get("section"),
                                                             "enable")
        self.settings['interval'] = self.localMgr.read_setting(self.settings.get("section"),
                                                               "interval")

        if self.scheduler.check_ticket(self.settings.get("section"),
                                       interval=self.settings.get("interval")):
            print("Remote Manager RUNNING...")
            await self.find_updates()
            await self.sync_updates()

    async def find_updates(self):
        self.configuration = Configuration(self.localMgr)
        self.logger.info("Remote Update Manager looking for updates")
        self.logger.debug(self.configuration.update())

    async def sync_updates(self):
        pass


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
