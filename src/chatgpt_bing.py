import aiohttp
from log import getlogger

logger = getlogger()


class GPTBOT:
    def __init__(
        self,
        api_endpoint: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self.api_endpoint = api_endpoint
        self.session = session

    async def queryBing(self, payload: dict) -> dict:
        resp = await self.session.post(url=self.api_endpoint, json=payload, timeout=300)
        status_code = resp.status
        if not status_code == 200:
            logger.warning(str(resp.reason))
            raise Exception(str(resp.reason))
        return await resp.json()

    async def queryChatGPT(self, payload: dict) -> dict:
        resp = await self.session.post(url=self.api_endpoint, json=payload, timeout=300)
        status_code = resp.status
        if not status_code == 200:
            logger.warning(str(resp.reason))
            raise Exception(str(resp.reason))
        return await resp.json()


async def test_chatgpt():
    session = aiohttp.ClientSession()
    gptbot = GPTBOT(api_endpoint="http://localhost:3000/conversation", session=session)
    payload = {}
    while True:
        prompt = input("Bob: ")
        payload["message"] = prompt
        payload.update(
            {
                "clientOptions": {
                    "clientToUse": "chatgpt",
                },
            },
        )
        resp = await gptbot.queryChatGPT(payload)
        content = resp["response"]
        payload["conversationId"] = resp["conversationId"]
        payload["parentMessageId"] = resp["messageId"]
        print("GPT: " + content)


async def test_bing():
    session = aiohttp.ClientSession()
    gptbot = GPTBOT(api_endpoint="http://localhost:3000/conversation", session=session)
    payload = {}
    while True:
        prompt = input("Bob: ")
        payload["message"] = prompt
        payload.update(
            {
                "clientOptions": {
                    "clientToUse": "bing",
                },
            },
        )
        resp = await gptbot.queryBing(payload)
        content = "".join(
            [body["text"] for body in resp["details"]["adaptiveCards"][0]["body"]],
        )
        payload["conversationSignature"] = resp["conversationSignature"]
        payload["conversationId"] = resp["conversationId"]
        payload["clientId"] = resp["clientId"]
        payload["invocationId"] = resp["invocationId"]
        print("Bing: " + content)


# if __name__ == "__main__":
# asyncio.run(test_chatgpt())
# asyncio.run(test_bing())
