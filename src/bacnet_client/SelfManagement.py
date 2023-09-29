
import asyncio
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
        self.subscribers = []
        self.build_options()
        self.logger = logging.getLogger('ClientLog')
        subprocess.run(["../res/resmgr.sh",
                        "../res/local-device.ini",
                        "../res/ioevents"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance

    def notify(self, opt, value):
        for sub in self.subscribers:
            try:
                for k, v in sub.settings.items():
                    if k == opt.option:
                        sub.update(opt.option, self.set_type(value))
            except Exception as e:
                self.logger.error(f"{e}")

    def subscribe(self, sub):
        self.subscribers.append(sub)

    def unsubscribe(self, sub):
        self.subscriptions.remove(sub)

    def build_options(self):
        self.config.read(f"{self.respath}local-device.ini")
        sections = self.config.sections()
        for section in sections:
            options = self.config.options(section)
            for option in options:
                value = self.set_type(self.config.get(section, option))
                self.options.append(Option(section, option, value))
        self.initialized = True

    # Deprecated (will remove soon)
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

    def set_type(self, value):
        typed_value = None
        if value == 'True' or value == 'False':
            typed_value = bool(value)
        else:
            try:
                typed_value = int(value)
            except ValueError:
                try:
                    typed_value = float(value)
                except ValueError:
                    typed_value = str(value)
        return typed_value

    def get_event_count(self, file_path):
        line_count = 0
        try:
            with open(file_path, "r") as file:
                line_count = sum(1 for line in file)
            self.logger.debug(f"{file_path} event count: {line_count}")
        except FileNotFoundError:
            self.logger.error(f"The file '{file_path}' was not found.")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        return line_count

    def clear_events(self, file_path):
        try:
            with open(file_path, "w") as file:
                self.logger.debug(f"clearing {file.name} events")
            self.logger.debug(f"The file '{file_path}' has been cleared.")
        except FileNotFoundError:
            self.logger.error(f"The file '{file_path}' was not found.")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")

    def sync(self):
        """
        This function runs inside the asyn function 'process_io_deltas'. It does the
        actual work of traversing the document tree and checking each option's mem/io delta
        and notifying all the subscribers of options with active deltas of the change.
        """
        self.logger.info("Performing configuration sync")
        self.config.read(f"{self.respath}local-device.ini")
        for option in self.options:
            self.logger.debug(f"current in-memory: {option.section} - {option.option} - {option.value}")
            update = self.set_type(self.config.get(option.section, option.option))
            option.value = update
            self.notify(option, update)

    async def proces_io_deltas(self):
        """
        This function creates and maintains a running instance of the bash inotifywait command
        It listens for stdout and every time the config file is modified a new event record is
        logged, and the 'sync' function runs.
        """
        last_event = 0
        while True:
            current_event = self.get_event_count(f"{self.respath}ioevents")
            self.logger.debug(f"current event#: {current_event} - last event#: {last_event}")

            if current_event > last_event:
                self.sync()
            if current_event >= 200:
                last_event = 0
                self.clear_events(f"{self.respath}ioevents")
            else:
                last_event = current_event
            await asyncio.sleep(60)


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


class Option(object):
    """
    The Option object is responsible for keeping the last known state for its parent section and its option value.
    It also maintains a list of Subscription objects which Subscribers must create and pass as an argument when
    calling to subscribe for change-of-value notifications for this option.
    The opton object is also able to check its state with another instance of the same file option to check for deltas.
    Lastly, the option object can notify its subscription base with the appropriate section and option state back to
    the subscribers.
    """
    def __init__(self, section: str, option: str, value):
        self.section = section
        self.option = option
        self.value = value
