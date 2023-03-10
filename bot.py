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
    ):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.device_id = device_id
        self.room_id = room_id
        self.api_key = api_key
        self.bing_api_endpoint = bing_api_endpoint
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
            self.bingbot = BingBot(bing_api_endpoint)

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

        # remove newline character from event.body
        event.body = re.sub("\r\n|\r|\n", " ", event.body)

        # chatgpt
        n = self.chat_prog.match(event.body)
        if n:
            if self.api_key != '':
                # sending typing state
                await self.client.room_typing(room_id)
                prompt = n.group(1)
                try:
                    # run synchronous function in different thread
                    text = await asyncio.to_thread(self.chatbot.ask, prompt)
                    text = text.strip()
                    await send_room_message(self.client, room_id, send_text=text,
                                            reply_to_event_id=reply_to_event_id)
                except Exception as e:
                    logger.error("Error", exc_info=True)
                    print(f"Error: {e}")
                    pass
            else:
                logger.warning("No API_KEY provided")
                await send_room_message(self.client, room_id, send_text="API_KEY not provided")

        m = self.gpt_prog.match(event.body)
        if m:
            # sending typing state
            await self.client.room_typing(room_id)
            prompt = m.group(1)
            try:
                # timeout 60s
                text = await asyncio.wait_for(ask(prompt, self.chatgpt_api_endpoint, self.headers), timeout=60)
            except TimeoutError:
                logger.error("timeoutException", exc_info=True)
                text = "Timeout error"

            text = text.strip()
            await send_room_message(self.client, room_id, send_text=text,
                                    reply_to_event_id=reply_to_event_id)

        # bing ai
        if self.bing_api_endpoint != '':
            b = self.bing_prog.match(event.body)
            if b:
                # sending typing state
                await self.client.room_typing(room_id)
                prompt = b.group(1)
                try:
                    # timeout 120s
                    text = await asyncio.wait_for(self.bingbot.ask_bing(prompt), timeout=120)
                except TimeoutError:
                    logger.error("timeoutException", exc_info=True)
                    text = "Timeout error"
                text = text.strip()
                await send_room_message(self.client, room_id, send_text=text,
                                        reply_to_event_id=reply_to_event_id)

    # bot login
    async def login(self) -> None:
        try:
            resp = await self.client.login(password=self.password)
            if not isinstance(resp, LoginResponse):
                logger.error("Login Failed")
                print(f"Login Failed: {resp}")
                sys.exit(1)
        except Exception as e:
            logger.error("Error Exception", exc_info=True)

    # sync messages in the room
    async def sync_forever(self, timeout=30000):
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        await self.client.sync_forever(timeout=timeout, full_state=True)
