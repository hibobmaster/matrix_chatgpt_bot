import sys
import asyncio
import re
import os
from typing import Optional
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse, AsyncClientConfig
from nio.store.database import SqliteStore
from ask_gpt import ask
from send_message import send_room_message
from v3 import Chatbot
from log import getlogger
from bing import BingBot
from BingImageGen import ImageGen
from send_image import send_room_image
"""
free api_endpoint from https://github.com/ayaka14732/ChatGPTAPIFree
"""
chatgpt_api_endpoint_list = {
    "free": "https://chatgpt-api.shn.hk/v1/",
    "paid": "https://api.openai.com/v1/chat/completions"
}
logger = getlogger()


class Bot:
    def __init__(
        self,
        homeserver: str,
        user_id: str,
        password: str,
        device_id: str,
        api_key: Optional[str] = "",
        room_id: Optional[str] = '',
        bing_api_endpoint: Optional[str] = '',
        access_token: Optional[str] = '',
        jailbreakEnabled: Optional[bool] = False,
        bing_auth_cookie: Optional[str] = '',
    ):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.device_id = device_id
        self.room_id = room_id
        self.api_key = api_key
        self.bing_api_endpoint = bing_api_endpoint
        self.jailbreakEnabled = jailbreakEnabled
        self.bing_auth_cookie = bing_auth_cookie
        # initialize AsyncClient object
        self.store_path = os.getcwd()
        self.config = AsyncClientConfig(store=SqliteStore,
                                        store_name="bot",
                                        store_sync_tokens=True,
                                        encryption_enabled=True,
                                        )
        self.client = AsyncClient(self.homeserver, user=self.user_id, device_id=self.device_id,
                                  config=self.config, store_path=self.store_path,)
        if access_token != '':
            self.client.access_token = access_token
        # regular expression to match keyword [!gpt {prompt}] [!chat {prompt}]
        self.gpt_prog = re.compile(r"^\s*!gpt\s*(.+)$")
        self.chat_prog = re.compile(r"^\s*!chat\s*(.+)$")
        self.bing_prog = re.compile(r"^\s*!bing\s*(.+)$")
        self.pic_prog = re.compile(r"^\s*!pic\s*(.+)$")
        self.help_prog = re.compile(r"^\s*!help\s*.*$")

        # initialize chatbot and chatgpt_api_endpoint
        if self.api_key != '':
            self.chatbot = Chatbot(api_key=self.api_key)

            self.chatgpt_api_endpoint = chatgpt_api_endpoint_list['paid']
            # request header for !gpt command
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            }
        else:
            self.chatgpt_api_endpoint = chatgpt_api_endpoint_list['free']
            self.headers = {
                "Content-Type": "application/json",
            }

        # initialize bingbot
        if self.bing_api_endpoint != '':
            self.bingbot = BingBot(bing_api_endpoint, jailbreakEnabled=self.jailbreakEnabled)

        # initialize BingImageGen
        if self.bing_auth_cookie != '':
            self.imageGen = ImageGen(self.bing_auth_cookie)

    # message_callback event
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self.room_id == '':
            room_id = room.room_id
        else:
            # if event room id does not match the room id in config, return
            if room.room_id != self.room_id:
                return
            room_id = self.room_id

        # reply event_id
        reply_to_event_id = event.event_id

        # print info to console
        print(
            f"Message received in room {room.display_name}\n"
            f"{room.user_name(event.sender)} | {event.body}"
        )

        if self.user_id != event.sender:
            # remove newline character from event.body
            event.body = re.sub("\r\n|\r|\n", " ", event.body)

            # chatgpt
            n = self.chat_prog.match(event.body)
            if n:
                prompt = n.group(1)
                if self.api_key != '':
                    await self.gpt(room_id, reply_to_event_id, prompt)
                else:
                    logger.warning("No API_KEY provided")
                    await send_room_message(self.client, room_id, send_text="API_KEY not provided")

            m = self.gpt_prog.match(event.body)
            if m:
                prompt = m.group(1)
                await self.chat(room_id, reply_to_event_id, prompt)

            # bing ai
            if self.bing_api_endpoint != '':
                b = self.bing_prog.match(event.body)
                if b:
                    prompt = b.group(1)
                    await self.bing(room_id, reply_to_event_id, prompt)

            # Image Generation by Microsoft Bing
            if self.bing_auth_cookie != '':
                i = self.pic_prog.match(event.body)
                if i:
                    prompt = i.group(1)
                    await self.pic(room_id, prompt)

            # help command
            h = self.help_prog.match(event.body)
            if h:
                await self.help(room_id)

    # !gpt command
    async def gpt(self, room_id, reply_to_event_id, prompt):
        await self.client.room_typing(room_id)
        try:
            # run synchronous function in different thread
            text = await asyncio.to_thread(self.chatbot.ask, prompt)
            text = text.strip()
            await send_room_message(self.client, room_id, send_text=text,
                                    reply_to_event_id=reply_to_event_id)
        except Exception as e:
            logger.error("Error", exc_info=True)
            print(f"Error: {e}")

    # !chat command
    async def chat(self, room_id, reply_to_event_id, prompt):
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            # timeout 120s
            text = await asyncio.wait_for(ask(prompt, self.chatgpt_api_endpoint, self.headers), timeout=120)
        except TimeoutError:
            logger.error("timeoutException", exc_info=True)
            text = "Timeout error"

        text = text.strip()
        try:
            await send_room_message(self.client, room_id, send_text=text,
                                    reply_to_event_id=reply_to_event_id)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # !bing command
    async def bing(self, room_id, reply_to_event_id, prompt):
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            # timeout 120s
            text = await asyncio.wait_for(self.bingbot.ask_bing(prompt), timeout=120)
        except TimeoutError:
            logger.error("timeoutException", exc_info=True)
            text = "Timeout error"
        text = text.strip()
        try:
            await send_room_message(self.client, room_id, send_text=text,
                                    reply_to_event_id=reply_to_event_id)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # !pic command
    async def pic(self, room_id, prompt):
        try:
            # generate image
            generated_image_path = self.imageGen.save_images(
                self.imageGen.get_images(prompt),
                "images",
            )
            # send image
            if generated_image_path != "":
                await send_room_image(self.client, room_id, generated_image_path)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # !help command
    async def help(self, room_id):
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            help_info = "!gpt [content], generate response without context conversation\n" + \
                        "!chat [content], chat with context conversation\n" + \
                        "!bing [content], chat with context conversation powered by Bing AI\n" + \
                        "!pic [prompt], Image generation by Microsoft Bing"

            await send_room_message(self.client, room_id, send_text=help_info)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # bot login
    async def login(self) -> None:
        try:
            resp = await self.client.login(password=self.password)
            if not isinstance(resp, LoginResponse):
                logger.error("Login Failed")
                print(f"Login Failed: {resp}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # sync messages in the room
    async def sync_forever(self, timeout=30000):
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        await self.client.sync_forever(timeout=timeout, full_state=True)
