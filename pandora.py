# https://github.com/pengzhile/pandora/blob/master/doc/HTTP-API.md
import uuid
import aiohttp
import asyncio


class Pandora:
    def __init__(self, api_endpoint: str, clientSession: aiohttp.ClientSession) -> None:
        self.api_endpoint = api_endpoint.rstrip("/")
        self.session = clientSession

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def gen_title(self, data: dict, conversation_id: str) -> None:
        """
        data = {
            "model": "",
            "message_id": "",
        }
        :param data: dict
        :param conversation_id: str
        :return: None
        """
        api_endpoint = (
            self.api_endpoint + f"/api/conversation/gen_title/{conversation_id}"
        )
        async with self.session.post(api_endpoint, json=data) as resp:
            return await resp.json()

    async def talk(self, data: dict) -> None:
        api_endpoint = self.api_endpoint + "/api/conversation/talk"
        """
        data = {
            "prompt": "",
            "model": "",
            "parent_message_id": "",
            "conversation_id": "", # ignore at the first time
            "stream": True,
        }
        :param data: dict
        :return: None
        """
        data["message_id"] = str(uuid.uuid4())
        async with self.session.post(api_endpoint, json=data) as resp:
            return await resp.json()

    async def goon(self, data: dict) -> None:
        """
        data = {
            "model": "",
            "parent_message_id": "",
            "conversation_id": "",
            "stream": True,
        }
        """
        api_endpoint = self.api_endpoint + "/api/conversation/goon"
        async with self.session.post(api_endpoint, json=data) as resp:
            return await resp.json()


async def test():
    model = "text-davinci-002-render-sha-mobile"
    api_endpoint = "http://127.0.0.1:8008"
    async with aiohttp.ClientSession() as session:
        client = Pandora(api_endpoint, session)
    conversation_id = None
    parent_message_id = str(uuid.uuid4())
    first_time = True
    async with client:
        while True:
            prompt = input("BobMaster: ")
            if conversation_id:
                data = {
                    "prompt": prompt,
                    "model": model,
                    "parent_message_id": parent_message_id,
                    "conversation_id": conversation_id,
                    "stream": False,
                }
            else:
                data = {
                    "prompt": prompt,
                    "model": model,
                    "parent_message_id": parent_message_id,
                    "stream": False,
                }
            response = await client.talk(data)
            conversation_id = response["conversation_id"]
            parent_message_id = response["message"]["id"]
            content = response["message"]["content"]["parts"][0]
            print("ChatGPT: " + content + "\n")
            if first_time:
                first_time = False
                data = {
                    "model": model,
                    "message_id": parent_message_id,
                }
                response = await client.gen_title(data, conversation_id)


if __name__ == "__main__":
    asyncio.run(test())
