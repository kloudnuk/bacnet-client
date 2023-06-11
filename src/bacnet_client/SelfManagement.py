
import configparser


class LocalManager(object):
    """
    Manage device to cloud registration, updates, notifications, security,
    and command/control pipeline.
    """

    __instance = None

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance
