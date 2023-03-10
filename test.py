from v3 import Chatbot
import asyncio
from ask_gpt import ask
import json
from bing import BingBot

fp = open("config.json", "r")
config = json.load(fp)
api_key = config.get('api_key', '')
bing_api_endpoint = config.get('bing_api_endpoint', '')
api_endpoint_list = {
    "free": "https://chatgpt-api.shn.hk/v1/",
    "paid": "https://api.openai.com/v1/chat/completions"
}


def test_v3(prompt: str):
    bot = Chatbot(api_key=api_key)
    resp = bot.ask(prompt=prompt)
    print(resp)


async def test_ask_gpt_paid(prompt: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    api_endpoint = api_endpoint_list['paid']
    # test ask_gpt.py ask()
    print(await ask(prompt, api_endpoint, headers))


async def test_ask_gpt_free(prompt: str):
    headers = {
        "Content-Type": "application/json",
    }
    api_endpoint = api_endpoint_list['free']
    print(await ask(prompt, api_endpoint, headers))


async def test_bingbot():
    if bing_api_endpoint != '':
        bingbot = BingBot(bing_api_endpoint)
        prompt1 = "Hello World"
        prompt2 = "Do you know Victor Marie Hugo"
        prompt3 = "Can you tell me something about him?"
        resp1 = await bingbot.ask_bing(prompt1)
        resp2 = await bingbot.ask_bing(prompt2)
        resp3 = await bingbot.ask_bing(prompt3)
        print(resp1)
        print(resp2)
        print(resp3)

if __name__ == "__main__":
    test_v3("Hello World")
    asyncio.run(test_ask_gpt_paid("Hello World"))
    asyncio.run(test_ask_gpt_free("Hello World"))
    asyncio.run(test_bingbot())
