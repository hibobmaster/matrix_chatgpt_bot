import aiohttp
import asyncio
import json
from log import getlogger
logger = getlogger()


async def ask(prompt: str, api_endpoint: str, headers: dict) -> str:
    jsons = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }
    async with aiohttp.ClientSession() as session:
        max_try = 5
        while max_try > 0:
            try:
                async with session.post(url=api_endpoint,
                                        json=jsons, headers=headers, timeout=30) as response:
                    status_code = response.status
                    if not status_code == 200:
                        # print failed reason
                        logger.warning(str(response.reason))
                        max_try = max_try - 1
                        # wait 2s
                        await asyncio.sleep(2)
                        continue

                    resp = await response.read()
                    await session.close()
                    return json.loads(resp)['choices'][0]['message']['content']
            except Exception as e:
                logger.error("Error Exception", exc_info=True)
                print(e)
                pass
