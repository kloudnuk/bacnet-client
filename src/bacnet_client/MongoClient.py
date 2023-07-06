
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

    async def writeDocument(self, document: dict, db, collectionName: str):
        result = None
        try:
            result = await db[collectionName].insert_one(document)
            print(repr(result.inserted_id))
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result}\n", "utf-8"))

    async def writeDocuments(self, documents: list, db, collectionName: str):
        result_set = None
        try:
            result_set = await db[collectionName].insert_many(documents)
            print(f"Number of devices added: {len(result_set.inserted_ids)}")
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}: {result_set}\n", "utf-8"))

    async def replaceDocument(self, document: dict, db, collectionName: str):
        result = await db[collectionName].find_one_and_replace({'id': document["id"]},
                                                               document)
        print(f"{result}")

    async def findDocuments(self, db, collectionName: str, query=None, projection=None):
        documents = []
        async for dev in db[collectionName].find(query, projection=projection):
            documents.append(dev)
        return documents
