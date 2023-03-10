import aiohttp
import json
import asyncio
from log import getlogger
# api_endpoint = "http://localhost:3000/conversation"
logger = getlogger()
python_boolean_to_json = {
    "true": True,
}


class BingBot:
    def __init__(self, bing_api_endpoint: str):
        self.data = {
            'jailbreakConversationId': json.dumps(python_boolean_to_json['true']),
            'clientOptions.clientToUse': 'bing'
        }
        self.bing_api_endpoint = bing_api_endpoint

    async def ask_bing(self, prompt) -> str:
        self.data['message'] = prompt
        async with aiohttp.ClientSession() as session:
            max_try = 5
            while max_try > 0:
                try:
                    resp = await session.post(url=self.bing_api_endpoint, json=self.data)
                    status_code = resp.status
                    body = await resp.read()
                    if not status_code == 200:
                        # print failed reason
                        logger.warning(str(resp.reason))
                        max_try = max_try - 1
                        # print(await resp.text())
                        await asyncio.sleep(2)
                        continue
                    json_body = json.loads(body)
                    # print(json_body['jailbreakConversationId'])
                    self.data['jailbreakConversationId'] = json_body['jailbreakConversationId']
                    self.data['parentMessageId'] = json_body['messageId']
                    return json_body['response']
                except Exception as e:
                    logger.error("Error Exception", exc_info=True)
                    print(f"Error: {e}")
                    pass
            return "Error, please retry"
