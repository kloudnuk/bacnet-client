
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
        self.last_event = 0
        self.logger = logging.getLogger('ClientLog')
        self.build_options()
        subprocess.run([f"{self.respath}ini_eventmgr.sh",
                        f"{self.respath}local-device.ini",
                        f"{self.respath}ini.events"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance

    def notify(self, opt, value):
        """
        Notify all configuration-change event subscribers so they can update their
        configuration settings during runtime.
        """
        for sub in self.subscribers:
            for k in sub.settings:
                if k == opt.option:
                    sub.update(opt.section, opt.option, self.set_type(value))

    def subscribe(self, sub):
        """
        Add services using the configuration file as change-event notification subscribers
        """
        self.subscribers.append(sub)

    def unsubscribe(self, sub):
        """
        Remove service from the subscription list
        """
        self.subscriptions.remove(sub)

    def build_options(self):
        """
        Initialize the in-memory configuration state. Flatten the configuration tree, into a
        list of Option objects with their corresponding attributes.
        """
        self.config.read(f"{self.respath}local-device.ini")
        sections = self.config.sections()
        for section in sections:
            options = self.config.options(section)
            for option in options:
                value = self.set_type(self.config.get(section, option))
                self.options.append(Option(section, option, value))
        self.initialized = True

    def read_setting(self, section, prop):
        self.config.read(f"{self.respath}local-device.ini")
        setting = self.set_type(self.config.get(section, prop))
        return setting

    @classmethod
    def set_type(self, value, option=None):
        """
        Provide type guarantee for the configuration setting's values as they are updated
        and sent to subscribers.
        """
        typed_value = None
        if value == "True":
            typed_value = True
        elif value == "False":
            typed_value = False
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
        """
        Get current recorded events tally, in order to compare with the last tally run, and
        identify when new events have occur.
        """
        line_count = self.last_event
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
        """"
        Reset the event count to zero at a certain point not to overflow its max size.
        """
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
        This function runs inside process_io_deltas'. It does the
        actual work of traversing the document tree and checking each option's mem/io delta
        and notifying all the subscribers to options with active deltas.
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
        This function runs forever in an io-loop task in app.py, it constantly checks current event count
        to last known count and if current count is higher, it triggers a delta sink which notifies all
        subscriber objects to update the corresponding configuration values. It's also in charge of running
        the count reset function.
        """
        while True:
            current_event = self.get_event_count(f"{self.respath}ini.events")

            if current_event > self.last_event:
                self.logger.debug(f"Delta sink initiated - current: {current_event} - last: {self.last_event}")
                self.sync()
            elif current_event < self.last_event:
                self.logger.debug(f"File lines and tally are out-of-sync - current: {current_event} - last: {self.last_event}")
                self.last_event = current_event

            if current_event > 5000:
                self.logger.debug(f"Max number of events reached, resetting: {current_event}")
                self.clear_events(f"{self.respath}ini.events")
                self.last_event = 0
            else:
                self.last_event = current_event
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
    The Option object is responsible for keeping track of state
    for its parent section and its option value.
    """
    def __init__(self, section: str, option: str, value):
        self.section = section
        self.option = option
        self.value = value
