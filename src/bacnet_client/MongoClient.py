
import sys
import configparser
import datetime
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient


class Mongodb():

    """
    MongoDB client singleton connects to the database server, and performs all CRUD operations
    """

    __instance = None

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read('local-device.ini')
        self.uri: str = str(self.config.get("mongodb", "connectionString"))
        self.client: AsyncIOMotorClient = \
            AsyncIOMotorClient(self.uri,
                               tls=True,
                               tlsCertificateKeyFile=self.config
                               .get("mongodb",
                                    "certpath"), server_api=ServerApi('1'))

    def __new__(cls):
        if Mongodb.__instance is None:
            Mongodb.__instance = object.__new__(cls)
        return Mongodb.__instance

    async def pingServer(self):
        try:
            await self.client.admin.command('ping')
            print(f"mongodb server ping ok...{datetime.datetime.now()}")
            return True
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return False

    def getDb(self):
        try:
            self.config.read('local-device.ini')
            dbName = self.config.get("mongodb", "dbname")
            return self.client[dbName]
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return None

    def getCollection(self, colName: str):
        return self.client[colName]

    async def getDocumentCount(self, db, collectionName: str):
        n = await db[collectionName].count_documents({})
        return n

    async def writeDevice(self, device: dict, db, collectionName: str):
        result = None
        try:
            result = await db[collectionName].insert_one(device)
            print(repr(result.inserted_id))
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result}\n", "utf-8"))

    async def writeDevices(self, devices: list, db, collectionName: str):
        result_set = None
        try:
            result_set = await db[collectionName].insert_many(devices)
            print(f"Number of devices added: {len(result_set.inserted_ids)}")
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result_set}\n", "utf-8"))

    async def replaceDevice(self, device: dict, db, collectionName: str):
        result = await db[collectionName].find_one_and_replace({'id': device["id"]},
                                                               device)
        print(f"{result}")
