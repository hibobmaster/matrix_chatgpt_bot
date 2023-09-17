import asyncio
import json
import os
from pathlib import Path
import signal
import sys

from bot import Bot
from log import getlogger

logger = getlogger()


async def main():
    need_import_keys = False
    config_path = Path(os.path.dirname(__file__)).parent / "config.json"
    if os.path.isfile(config_path):
        try:
            fp = open(config_path, encoding="utf8")
            config = json.load(fp)
        except Exception:
            logger.error("config.json load error, please check the file")
            sys.exit(1)

        matrix_bot = Bot(
            homeserver=config.get("homeserver"),
            user_id=config.get("user_id"),
            password=config.get("password"),
            device_id=config.get("device_id"),
            room_id=config.get("room_id"),
            import_keys_path=config.get("import_keys_path"),
            import_keys_password=config.get("import_keys_password"),
            openai_api_key=config.get("openai_api_key"),
            gpt_api_endpoint=config.get("gpt_api_endpoint"),
            gpt_model=config.get("gpt_model"),
            max_tokens=int(config.get("max_tokens")),
            top_p=float(config.get("top_p")),
            presence_penalty=float(config.get("presence_penalty")),
            frequency_penalty=float(config.get("frequency_penalty")),
            reply_count=int(config.get("reply_count")),
            system_prompt=config.get("system_prompt"),
            temperature=float(config.get("temperature")),
            flowise_api_url=config.get("flowise_api_url"),
            flowise_api_key=config.get("flowise_api_key"),
            image_generation_endpoint=config.get("image_generation_endpoint"),
            image_generation_backend=config.get("image_generation_backend"),
            timeout=float(config.get("timeout")),
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
            import_keys_path=os.environ.get("IMPORT_KEYS_PATH"),
            import_keys_password=os.environ.get("IMPORT_KEYS_PASSWORD"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            gpt_api_endpoint=os.environ.get("GPT_API_ENDPOINT"),
            gpt_model=os.environ.get("GPT_MODEL"),
            max_tokens=int(os.environ.get("MAX_TOKENS")),
            top_p=float(os.environ.get("TOP_P")),
            presence_penalty=float(os.environ.get("PRESENCE_PENALTY")),
            frequency_penalty=float(os.environ.get("FREQUENCY_PENALTY")),
            reply_count=int(os.environ.get("REPLY_COUNT")),
            system_prompt=os.environ.get("SYSTEM_PROMPT"),
            temperature=float(os.environ.get("TEMPERATURE")),
            flowise_api_url=os.environ.get("FLOWISE_API_URL"),
            flowise_api_key=os.environ.get("FLOWISE_API_KEY"),
            image_generation_endpoint=os.environ.get("IMAGE_GENERATION_ENDPOINT"),
            image_generation_backend=os.environ.get("IMAGE_GENERATION_BACKEND"),
            timeout=float(os.environ.get("TIMEOUT")),
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

    sync_task = asyncio.create_task(
        matrix_bot.sync_forever(timeout=30000, full_state=True)
    )

    # handle signal interrupt
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda: asyncio.create_task(matrix_bot.close(sync_task)),
        )

    await sync_task


if __name__ == "__main__":
    logger.info("matrix chatgpt bot start.....")
    asyncio.run(main())
