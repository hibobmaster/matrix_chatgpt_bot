import aiohttp
import asyncio
import json
from log import getlogger
logger = getlogger()


class askGPT:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def oneTimeAsk(self, prompt: str, api_endpoint: str, headers: dict) -> str:
        jsons = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }
        max_try = 3
        while max_try > 0:
            try:
                async with self.session.post(url=api_endpoint,
                                             json=jsons, headers=headers, timeout=60) as response:
                    status_code = response.status
                    if not status_code == 200:
                        # print failed reason
                        logger.warning(str(response.reason))
                        max_try = max_try - 1
                        # wait 2s
                        await asyncio.sleep(2)
                        continue

                    resp = await response.read()
                    return json.loads(resp)['choices'][0]['message']['content']
            except Exception as e:
                raise Exception(e)
