

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
        print("todo")

    def __new__(cls):
        if LocalManager.__instance is None:
            LocalManager.__instance = object.__new__(cls)
        return LocalManager.__instance
