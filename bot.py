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


class Bot:
    def __init__(
         self,
         homeserver: str,
         user_id: str,
         password: str,
         device_id: str,
         api_key: Optional[str] = "",
         room_id: Optional[str] = '',
    ):
        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.device_id = device_id
        self.room_id = room_id
        self.api_key = api_key
        # initialize AsyncClient object
        self.store_path = os.getcwd()
        self.config = AsyncClientConfig(store=SqliteStore,
                                        store_name="bot",
                                        store_sync_tokens=True,
                                        )
        self.client = AsyncClient(self.homeserver, user=self.user_id, device_id=self.device_id,
                                  config=self.config, store_path=self.store_path)
        # regular expression to match keyword [!gpt {prompt}] [!chat {prompt}]
        self.gpt_prog = re.compile(r"^\s*!gpt\s*(.+)$")
        self.chat_prog = re.compile(r"^\s*!chat\s*(.+)$")
        # initialize chatbot
        if self.api_key != '':
            self.chatbot = Chatbot(api_key=self.api_key)

    # message_callback event
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self.room_id == '':
            room_id = room.room_id
        else:
            room_id = self.room_id
        # chatgpt
        m = self.gpt_prog.match(event.body)
        if m:
            # sending typing state
            await self.client.room_typing(room_id)
            prompt = m.group(1)
            text = await ask(prompt)
            text = text.strip()
            await send_room_message(self.client, room_id, send_text=text)

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
                    await send_room_message(self.client, room_id, send_text=text)
                except Exception as e:
                    print(f"Error: {e}")
                    pass
            else:
                await send_room_message(self.client, room_id, send_text="API_KEY not provided")

        # print info to console
        # print(
        #     f"Message received in room {room.display_name}\n"
        #     f"{room.user_name(event.sender)} | {event.body}"
        # )

    # bot login
    async def login(self) -> None:
        resp = await self.client.login(password=self.password)
        if not isinstance(resp, LoginResponse):
            print(f"Login Failed: {resp}")
            sys.exit(1)

    # sync messages in the room
    async def sync_forever(self, timeout=30000):
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        await self.client.sync_forever(timeout=timeout, full_state=True)
