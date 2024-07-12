import sys
import logging
import pymongo
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from .SelfManagement import LocalManager, Subscriber


class Mongodb(Subscriber):
    """
    MongoDB client singleton connects to the database server, and performs all CRUD operations
    """

    __instance = None
    __ini_section = "mongodb"

    def __init__(self) -> None:
        self.localMgr: LocalManager = LocalManager()
        self.settings = {
            "section": Mongodb.__ini_section,
            "connectionString": self.localMgr.read_setting(
                Mongodb.__ini_section, "connectionString"
            ),
            "certpath": self.localMgr.read_setting(Mongodb.__ini_section, "certpath"),
            "dbname": self.localMgr.read_setting(Mongodb.__ini_section, "dbname"),
        }
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(
            self.settings.get("connectionString"),
            tls=True,
            tlsCertificateKeyFile=self.settings.get("certpath"),
            server_api=ServerApi("1"),
        )
        self.logger = logging.getLogger("ClientLog")

        if self.localMgr.initialized is True:
            self.localMgr.subscribe(self.__instance)

    def __new__(cls):
        if Mongodb.__instance is None:
            Mongodb.__instance = object.__new__(cls)
        return Mongodb.__instance

    def update(self, section, option, value):
        if section in self.settings.get("section"):
            oldvalue = self.settings.get(option)
            self.settings[option] = value
            self.logger.debug(f"{section}: {oldvalue} > {self.settings.get(option)}")

    async def pingServer(self):
        try:
            await self.client.admin.command("ping")
            self.logger.info("mongodb server ping ok...")
            return True
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}\n", "utf-8"))
            return False

    def getDb(self):
        try:
            return self.client[self.settings.get("dbname")]
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
            self.logger.debug(
                f"Number of documentss added: {len(result_set.inserted_ids)}"
            )
        except Exception as e:
            self.logger.error(f"{e}")

    async def replaceDocument(self, document: dict, db, collectionName: str):
        await db[collectionName].find_one_and_replace({"id": document["id"]}, document)

    async def findDocument(self, db, collectionName: str, query=None):
        return await db[collectionName].find_one(query)

    async def findDocuments(self, db, collectionName: str, query=None, projection=None):
        documents = []
        async for doc in db[collectionName].find(query, projection=projection):
            documents.append(doc)
        return documents

    async def updateFields(self, db, collectionName: str, query=None, update=None):
        return await db[collectionName].update_one(query, {"$set": update})

    async def watch_collection(self, db, collectionName, pipeline, target):
        resume_token = None
        try:
            async with db[collectionName].watch(pipeline) as stream:
                async for change_event in stream:
                    self.logger.debug(f"config-event: {change_event}")
                    await target.ingest(change_event)
                    resume_token = stream.resume_token
        except pymongo.errors.PyMongoError:
            # The ChangeStream encountered an unrecoverable error or the
            # resume attempt failed to recreate the cursor.
            if resume_token is None:
                self.logger.error(
                    "There is no usable resume token because there was a"
                    " failure during ChangeStream initialization."
                )
            else:
                # Use the interrupted ChangeStream's resume token to
                # create a new ChangeStream. The new stream will
                # continue from the last seen insert change without
                # missing any events.
                async with db[collectionName].watch(
                    pipeline, resume_after=resume_token
                ) as stream:
                    async for change_event in stream:
                        self.logger.debug(f"config-event: {change_event}")
                        await target.ingest(change_event)
