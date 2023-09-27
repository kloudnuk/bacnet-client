import asyncio
from bacnet_client import app


async def main():
    await app.main()

if __name__ == "__main__":
    asyncio.run(main())
