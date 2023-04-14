import aiohttp
import json
import asyncio
from log import getlogger
# api_endpoint = "http://localhost:3000/conversation"
logger = getlogger()


class BingBot:
    def __init__(self, session: aiohttp.ClientSession, bing_api_endpoint: str, jailbreakEnabled: bool = True):
        self.data = {
            'clientOptions.clientToUse': 'bing',
        }
        self.bing_api_endpoint = bing_api_endpoint

        self.session = session

        self.jailbreakEnabled = jailbreakEnabled

        if self.jailbreakEnabled:
            self.data['jailbreakConversationId'] = True

    async def ask_bing(self, prompt) -> str:
        self.data['message'] = prompt
        max_try = 2
        while max_try > 0:
            try:
                resp = await self.session.post(url=self.bing_api_endpoint, json=self.data, timeout=120)
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
                if self.jailbreakEnabled:
                    self.data['jailbreakConversationId'] = json_body['jailbreakConversationId']
                    self.data['parentMessageId'] = json_body['messageId']
                else:
                    self.data['conversationSignature'] = json_body['conversationSignature']
                    self.data['conversationId'] = json_body['conversationId']
                    self.data['clientId'] = json_body['clientId']
                    self.data['invocationId'] = json_body['invocationId']
                return json_body['details']['adaptiveCards'][0]['body'][0]['text']
            except Exception as e:
                logger.error("Error Exception", exc_info=True)
            
        
        return "Error, please retry"
