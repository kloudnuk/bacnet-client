import asyncio
import argparse
from bacnet_client import app


async def main():
    parser = argparse.ArgumentParser(description="BACnet Client")
    parser.add_argument("--respath", type=str, help="app's resource directory")
    respath = parser.parse_args().respath

    await app.main(respath)

if __name__ == "__main__":
    asyncio.run(main())
