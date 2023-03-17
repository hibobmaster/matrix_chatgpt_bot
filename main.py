#!/usr/bin/env python3
import json
import asyncio
from bot import Bot


async def main():
    fp = open('config.json', 'r')
    config = json.load(fp)
    matrix_bot = Bot(homeserver=config['homeserver'],
                     user_id=config['user_id'],
                     password=config.get('password', ''), # provide a default value when the key does not exist
                     device_id=config['device_id'],
                     room_id=config.get('room_id', ''),
                     api_key=config.get('api_key', ''),
                     bing_api_endpoint=config.get('bing_api_endpoint', ''),
                     access_token=config.get('access_token', ''),
                     jailbreakEnabled=config.get('jailbreakEnabled', False),
                     )
    if config.get('access_token', '') == '':
        await matrix_bot.login()
    await matrix_bot.sync_forever()


if __name__ == "__main__":
    print("matrix chatgpt bot start.....")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(main())
