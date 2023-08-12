
import configparser


class LocalManager(object):
    """
    Manage bacnet device settings from cloud based UI.
    """

    __instance = None

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance
