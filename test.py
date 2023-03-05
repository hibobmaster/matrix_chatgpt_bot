from v3 import Chatbot
import asyncio
from ask_gpt import ask
import json
fp = open("config.json", "r")
config = json.load(fp)


def test_v3(prompt: str):
    bot = Chatbot(api_key=config['api_key'])
    resp = bot.ask(prompt=prompt)
    print(resp)


async def test_ask(prompt: str):
    print(await ask(prompt=prompt))

if __name__ == "__main__":
    test_v3("Hello World")
    asyncio.run(test_ask("Hello World"))
