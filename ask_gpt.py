"""
api_endpoint from https://github.com/ayaka14732/ChatGPTAPIFree
"""
import aiohttp
import asyncio
import json

api_endpoint_free = "https://chatgpt-api.shn.hk/v1/"
headers = {'Content-Type': "application/json"}


async def ask(prompt: str) -> str:
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

        while True:
            try:
                async with session.post(url=api_endpoint_free,
                                        json=jsons, headers=headers, timeout=10) as response:
                    status_code = response.status
                    if not status_code == 200:
                        # wait 2s
                        await asyncio.sleep(2)
                        continue

                    resp = await response.read()
                    await session.close()
                    return json.loads(resp)['choices'][0]['message']['content']
            except Exception as e:
                print(e)
                pass


async def test() -> None:
    resp = await ask("Hello World")
    print(resp)
    # type: str
    print(type(resp))


if __name__ == "__main__":
    asyncio.run(test())
