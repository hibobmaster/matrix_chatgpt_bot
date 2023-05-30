import asyncio
import json
import os
from bot import Bot
from log import getlogger

logger = getlogger()


async def main():
    need_import_keys = False
    if os.path.exists("config.json"):
        fp = open("config.json", "r", encoding="utf8")
        config = json.load(fp)

        matrix_bot = Bot(
            homeserver=config.get("homeserver"),
            user_id=config.get("user_id"),
            password=config.get("password"),
            device_id=config.get("device_id"),
            room_id=config.get("room_id"),
            api_key=config.get("api_key"),
            bing_api_endpoint=config.get("bing_api_endpoint"),
            access_token=config.get("access_token"),
            bard_token=config.get("bard_token"),
            jailbreakEnabled=config.get("jailbreakEnabled"),
            bing_auth_cookie=config.get("bing_auth_cookie"),
            markdown_formatted=config.get("markdown_formatted"),
            output_four_images=config.get("output_four_images"),
            import_keys_path=config.get("import_keys_path"),
            import_keys_password=config.get("import_keys_password"),
            flowise_api_url=config.get("flowise_api_url"),
            flowise_api_key=config.get("flowise_api_key"),
            pandora_api_endpoint=config.get("pandora_api_endpoint"),
            pandora_api_model=config.get("pandora_api_model"),
        )
        if (
            config.get("import_keys_path")
            and config.get("import_keys_password") is not None
        ):
            need_import_keys = True

    else:
        matrix_bot = Bot(
            homeserver=os.environ.get("HOMESERVER"),
            user_id=os.environ.get("USER_ID"),
            password=os.environ.get("PASSWORD"),
            device_id=os.environ.get("DEVICE_ID"),
            room_id=os.environ.get("ROOM_ID"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            bing_api_endpoint=os.environ.get("BING_API_ENDPOINT"),
            access_token=os.environ.get("ACCESS_TOKEN"),
            bard_token=os.environ.get("BARD_TOKEN"),
            jailbreakEnabled=os.environ.get("JAILBREAKENABLED", "false").lower()
            in ("true", "1", "t"),
            bing_auth_cookie=os.environ.get("BING_AUTH_COOKIE"),
            markdown_formatted=os.environ.get("MARKDOWN_FORMATTED", "false").lower()
            in ("true", "1", "t"),
            output_four_images=os.environ.get("OUTPUT_FOUR_IMAGES", "false").lower()
            in ("true", "1", "t"),
            import_keys_path=os.environ.get("IMPORT_KEYS_PATH"),
            import_keys_password=os.environ.get("IMPORT_KEYS_PASSWORD"),
            flowise_api_url=os.environ.get("FLOWISE_API_URL"),
            flowise_api_key=os.environ.get("FLOWISE_API_KEY"),
            pandora_api_endpoint=os.environ.get("PANDORA_API_ENDPOINT"),
            pandora_api_model=os.environ.get("PANDORA_API_MODEL"),
        )
        if (
            os.environ.get("IMPORT_KEYS_PATH")
            and os.environ.get("IMPORT_KEYS_PASSWORD") is not None
        ):
            need_import_keys = True

    await matrix_bot.login()
    if need_import_keys:
        logger.info("start import_keys process, this may take a while...")
        await matrix_bot.import_keys()
    await matrix_bot.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    logger.info("matrix chatgpt bot start.....")
    asyncio.run(main())
