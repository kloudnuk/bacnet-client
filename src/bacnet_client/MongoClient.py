"""
"""

import sys
import configparser
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient


class MongoDB():
    def __init__(self) -> None:
        self.uri: str = ""  # noqa: E501
        self.client: AsyncIOMotorClient = \
            AsyncIOMotorClient(self.uri,
                               tls=True,
                               tlsCertificateKeyFile='../res/X509-cert-bacnetclient01.pem',  # noqa: E501
                               server_api=ServerApi('1'))

    async def ping_server(self):
        try:
            await self.client.admin.command('ping')
            print("mongodb server ping ok...")
        except Exception as e:
            sys.stderr.buffer.write(bytes(f"{e}"))
