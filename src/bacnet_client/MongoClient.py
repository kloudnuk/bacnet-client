"""
MongoDB client singleton connects to the database server, and performs all CRUD operations
"""

import sys
import configparser
import datetime
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient


class Mongodb():
    __instance = None
    __config = configparser.ConfigParser()
    __config.read('local-device.ini')
    __uri: str = str(__config.get("mongodb", "connectionString"))
    __client: AsyncIOMotorClient = \
        AsyncIOMotorClient(__uri,
                           tls=True,
                           tlsCertificateKeyFile=__config
                           .get("mongodb",
                                "certpath"), server_api=ServerApi('1'))

    def __init__(cls) -> None:
        pass

    def __new__(cls):
        if Mongodb.__instance is None:
            Mongodb.__instance = object.__new__(cls)
        return Mongodb.__instance

    async def pingServer():
        try:
            await Mongodb.__client.admin.command('ping')
            print(f"mongodb server ping ok...{datetime.datetime.now()}")
            return True
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return False

    def getDb():
        try:
            Mongodb.__config.read('local-device.ini')
            dbName = Mongodb.__config.get("mongodb", "dbname")
            return Mongodb.__client[dbName]
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return None

    def getCollection(colName: str):
        return Mongodb.__client[colName]

    async def writeDevice(device: dict, db, collectionName: str):
        result = None
        try:
            result = await db[collectionName].insert_one(device)
            print(repr(result.inserted_id))
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result}\n", "utf-8"))

    async def writeDevices(devices: list, db, collectionName: str):
        result_set = None
        try:
            result_set = await db[collectionName].insert_many(devices)
            print(f"Number of devices added: {len(result_set.inserted_ids)}")
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result_set}\n", "utf-8"))
