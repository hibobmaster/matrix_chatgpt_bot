#!/usr/bin/env python3
import json
import asyncio
from bot import Bot
import sys


async def main():
    fp = open('config.json', 'r')
    config = json.load(fp)
    matrix_bot = Bot(homeserver=config['homeserver'],
                     user_id=config['user_id'],
                     password=config['password'],
                     device_id=config['device_id'],
                     room_id=config['room_id'],
                     api_key=config['api_key'])
    await matrix_bot.login()
    await matrix_bot.sync_forever()


if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(main())
    except KeyboardInterrupt:
        loop.close()
        sys.exit(0)

    # asyncio.get_event_loop().run_until_complete(main())
