import json
import os
import asyncio
from bot import Bot
from log import getlogger

logger = getlogger()

async def main():
    
    fp = open('config.json', 'r', encoding="utf8")
    config = json.load(fp)
    
    matrix_bot = Bot(homeserver=config.get('homeserver'),
                     user_id=config.get('user_id') ,
                     password=config.get('password'),
                     device_id=config.get('device_id'),
                     room_id=config.get('room_id'),
                     api_key=config.get('api_key'),
                     bing_api_endpoint=config.get('bing_api_endpoint'),
                     access_token=config.get('access_token'),
                     jailbreakEnabled=config.get('jailbreakEnabled'),
                     bing_auth_cookie=config.get('bing_auth_cookie'),
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

    await matrix_bot.sync_encryption_key()

    await matrix_bot.trust_own_devices()

    await matrix_bot.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    print("matrix chatgpt bot start.....")
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    asyncio.run(main())

        
