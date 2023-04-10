#!/usr/bin/env python3
import json
import os
import asyncio
from bot import Bot
from nio import Api, SyncResponse
from log import getlogger

logger = getlogger()

async def main():
    if os.path.exists('config.json'):
        fp = open('config.json', 'r', encoding="utf8")
        config = json.load(fp)
    
    matrix_bot = Bot(homeserver=os.environ.get("HOMESERVER") or config.get('homeserver'),
                     user_id=os.environ.get("USER_ID") or config.get('user_id') ,
                     password=os.environ.get("PASSWORD") or config.get('password'),
                     device_id=os.environ.get("DEVICE_ID") or config.get('device_id'),
                     room_id=os.environ.get("ROOM_ID") or config.get('room_id'),
                     api_key=os.environ.get("OPENAI_API_KEY") or config.get('api_key'),
                     bing_api_endpoint=os.environ.get("BING_API_ENDPOINT") or config.get('bing_api_endpoint'),
                     access_token=os.environ.get("ACCESS_TOKEN") or config.get('access_token'),
                     jailbreakEnabled=os.environ.get("JAILBREAKENABLED", "False").lower() in ('true', '1') or config.get('jailbreakEnabled'),
                     bing_auth_cookie=os.environ.get("BING_AUTH_COOKIE") or config.get('bing_auth_cookie'),
                     )
    # if not set access_token, then login via password
    # if os.path.exists('config.json'):
    #     fp = open('config.json', 'r', encoding="utf8")
    #     config = json.load(fp)
    #     if os.environ.get("ACCESS_TOKEN") is None and config.get("access_token") is None:
    #         await matrix_bot.login()
  
    # elif os.environ.get("ACCESS_TOKEN") is None:
    #             await matrix_bot.login()                         

    await matrix_bot.login()

    # await matrix_bot.sync_encryption_key()

    # await matrix_bot.trust_own_devices()

    try: 
        await matrix_bot.sync_forever(timeout=3000, full_state=True)
    finally:
        await matrix_bot.client.close()


if __name__ == "__main__":
    logger.debug("matrix chatgpt bot start.....")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(main())
