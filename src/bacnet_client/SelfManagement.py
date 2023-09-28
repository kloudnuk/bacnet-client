
import subprocess
import logging
import argparse
import configparser
from abc import ABC, abstractmethod


class LocalManager(object):
    """
    Manage bacnet device settings from cloud based UI.
    """

    __instance = None

    def __init__(self) -> None:
        # TODO - this script create a connection between the gateway's database document and the configuration file (ini) in the app space.
        #        Each Database can have multiple buildings and gateways can be grouped per the buiding they are located in and serve.
        #        Users will be able to update gateway setting via the api using the db as intermediary. Updates are not inmediate however and
        #        depend on the update rate selected in the configuration.

        parser = argparse.ArgumentParser(description="BACnet Client")
        parser.add_argument("--respath", type=str, help="app's resource directory")
        self.respath: str = parser.parse_args().respath
        self.config = configparser.ConfigParser()
        self.initialized = False
        self.options = []
        self.build_options()
        self.logger = logging.getLogger('ClientLog')
        self.complete = subprocess.run(["../res/resmgr.sh",
                                        "../res/local-device.ini",
                                        "../res/ioevents"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance

    def build_options(self):
        self.config.read(f"{self.respath}local-device.ini")
        sections = self.config.sections()
        for section in sections:
            options = self.config.options(section)
            for option in options:
                self.options.append(Option(section, option))
        self.initialized = True

    def read_setting(self, section, prop):
        self.config.read(f"{self.respath}local-device.ini")
        setting = str(self.config.get(section, prop))
        if prop == "enable":
            if setting == "True":
                setting = True
            else:
                setting = False
        elif prop == "interval" or prop == "timeout":
            setting = int(setting)
        return setting

    def sync(self):
        """
        This function runs inside the asyn function 'process_io_deltas'. It does the
        actual work of traversing the document tree and checking each option's mem/io delta
        and notifying all the subscribers of options with active deltas of the change.
        """
        print("Performing configuration sync")

    def proces_io_deltas(self):
        """
        This function creates and maintains a running instance of the bash inotifywait command
        It listens for stdout and every time the config file is modified a new event record is
        logged, and the 'sync' function runs.
        """


class Subscription(object):
    """
    Object defining a relationship between a subscriber and its configuration context.
    It's used to notify the subscriber object back when the section/option state changes value.
    """
    def __init__(self, section: str, option: str, value) -> None:
        self.section = section
        self.option = option
        if value == 'True' or value == 'False':
            self.value = bool(value)
        else:
            try:
                self.value = int(value)
            except ValueError:
                try:
                    self.value = float(value)
                except ValueError:
                    self.value = str(value)


class Option(object):
    """
    The Option object is responsible for keeping the last known state for its parent section and its option value.
    It also maintains a list of Subscription objects which Subscribers must create and pass as an argument when
    calling to subscribe for change-of-value notifications for this option.
    The opton object is also able to check its state with another instance of the same file option to check for deltas.
    Lastly, the option object can notify its subscription base with the appropriate section and option state back to
    the subscribers.
    """
    def __init__(self, section: str, option: str):
        self.section = section
        self.option = option
        self.subscriptions = [Subscription]

    def has_delta(self, option: str):
        eval_option: Option = Option(self.section, option)
        result: bool = True
        if self.value == eval_option.value:
            result = False
        return result

    def notify(self):
        for sub in self.subscriptions:
            sub.subscriber.update(sub)

    def subscribe(self, sub: Subscription):
        self.subscriptions.append(sub)

    def unsubscribe(self, sub: Subscription):
        self.subscriptions.remove(sub)


class Subscriber(ABC):
    """
    This abstract class acts as an interface and any class extending it
    must implement the update method so the Option's notify function can
    call it for each of its subscribers. So any subscriber should extend
    the interface by implementing the method signature.
    """
    @abstractmethod
    def update(self, subscription):
        pass
