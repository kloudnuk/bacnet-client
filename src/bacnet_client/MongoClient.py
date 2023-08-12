
import sys
import configparser
import logging
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient


class Mongodb():

    """
    MongoDB client singleton connects to the database server, and performs all CRUD operations
    """

    __instance = None

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read('../res/local-device.ini')
        self.uri: str = str(self.config.get("mongodb", "connectionString"))
        self.client: AsyncIOMotorClient = \
            AsyncIOMotorClient(self.uri,
                               tls=True,
                               tlsCertificateKeyFile=self.config
                               .get("mongodb",
                                    "certpath"), server_api=ServerApi('1'))
        self.logger = logging.getLogger('ClientLog')

    def __new__(cls):
        if Mongodb.__instance is None:
            Mongodb.__instance = object.__new__(cls)
        return Mongodb.__instance

    async def pingServer(self):
        try:
            await self.client.admin.command('ping')
            self.logger.info("mongodb server ping ok...")
            return True
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return False

    def getDb(self):
        try:
            self.config.read('../res/local-device.ini')
            dbName = self.config.get("mongodb", "dbname")
            return self.client[dbName]
        except Exception as e:
            self.logger.critical(f"{e}")
            return None

    def getCollection(self, colName: str):
        return self.client[colName]

    async def getDocumentCount(self, db, collectionName: str):
        n = await db[collectionName].count_documents({})
        return n

    async def writeDocument(self, document: dict, db, collectionName: str):
        try:
            await db[collectionName].insert_one(document)
        except Exception as e:
            self.logger.error(f"{e}")

    async def writeDocuments(self, documents: list, db, collectionName: str):
        result_set = None
        try:
            result_set = await db[collectionName].insert_many(documents)
            self.logger.debug(f"Number of documentss added: {len(result_set.inserted_ids)}")
        except Exception as e:
            self.logger.error(f"{e}")

    async def replaceDocument(self, document: dict, db, collectionName: str):
        await db[collectionName].find_one_and_replace({'id': document["id"]},
                                                      document)

    async def findDocuments(self, db, collectionName: str, query=None, projection=None):
        documents = []
        async for doc in db[collectionName].find(query, projection=projection):
            documents.append(doc)
        return documents

    async def updateFields(self, db, collectionName: str, query=None, update=None):
        return await db[collectionName].update_one(query, {'$set': update})
