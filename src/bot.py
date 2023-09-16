import asyncio
import os
from pathlib import Path
import re
import sys
import traceback
from typing import Union, Optional

import httpx

from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    JoinError,
    KeyVerificationCancel,
    KeyVerificationEvent,
    EncryptionError,
    KeyVerificationKey,
    KeyVerificationMac,
    KeyVerificationStart,
    LocalProtocolError,
    LoginResponse,
    MatrixRoom,
    MegolmEvent,
    RoomMessageText,
    ToDeviceError,
)
from nio.store.database import SqliteStore

from log import getlogger
from send_image import send_room_image
from send_message import send_room_message
from flowise import flowise_query
from gptbot import Chatbot

logger = getlogger()
DEVICE_NAME = "MatrixChatGPTBot"
GENERAL_ERROR_MESSAGE = "Something went wrong, please try again or contact admin."


class Bot:
    def __init__(
        self,
        homeserver: str,
        user_id: str,
        password: Union[str, None] = None,
        device_id: str = "MatrixChatGPTBot",
        room_id: Union[str, None] = None,
        import_keys_path: Optional[str] = None,
        import_keys_password: Optional[str] = None,
        openai_api_key: Union[str, None] = None,
        gpt_api_endpoint: Optional[str] = None,
        gpt_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        reply_count: Optional[int] = None,
        system_prompt: Optional[str] = None,
        temperature: Union[float, None] = None,
        flowise_api_url: Optional[str] = None,
        flowise_api_key: Optional[str] = None,
        timeout: Union[float, None] = None,
    ):
        if homeserver is None or user_id is None or device_id is None:
            logger.warning("homeserver && user_id && device_id is required")
            sys.exit(1)

        if password is None:
            logger.warning("password is required")
            sys.exit(1)

        self.homeserver: str = homeserver
        self.user_id: str = user_id
        self.password: str = password
        self.device_id: str = device_id
        self.room_id: str = room_id

        self.openai_api_key: str = openai_api_key
        self.gpt_api_endpoint: str = (
            gpt_api_endpoint or "https://api.openai.com/v1/chat/completions"
        )
        self.gpt_model: str = gpt_model or "gpt-3.5-turbo"
        self.max_tokens: int = max_tokens or 4000
        self.top_p: float = top_p or 1.0
        self.temperature: float = temperature or 0.8
        self.presence_penalty: float = presence_penalty or 0.0
        self.frequency_penalty: float = frequency_penalty or 0.0
        self.reply_count: int = reply_count or 1
        self.system_prompt: str = (
            system_prompt
            or "You are ChatGPT, \
            a large language model trained by OpenAI. Respond conversationally"
        )

        self.import_keys_path: str = import_keys_path
        self.import_keys_password: str = import_keys_password
        self.flowise_api_url: str = flowise_api_url
        self.flowise_api_key: str = flowise_api_key

        self.timeout: float = timeout or 120.0

        self.base_path = Path(os.path.dirname(__file__)).parent

        self.httpx_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
        )

        # initialize AsyncClient object
        self.store_path = self.base_path
        self.config = AsyncClientConfig(
            store=SqliteStore,
            store_name="sync_db",
            store_sync_tokens=True,
            encryption_enabled=True,
        )
        self.client = AsyncClient(
            homeserver=self.homeserver,
            user=self.user_id,
            device_id=self.device_id,
            config=self.config,
            store_path=self.store_path,
        )

        # initialize Chatbot object
        self.chatbot = Chatbot(
            aclient=self.httpx_client,
            api_key=self.openai_api_key,
            api_url=self.gpt_api_endpoint,
            engine=self.gpt_model,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            reply_count=self.reply_count,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
        )

        # setup event callbacks
        self.client.add_event_callback(self.message_callback, (RoomMessageText,))
        self.client.add_event_callback(self.decryption_failure, (MegolmEvent,))
        self.client.add_event_callback(self.invite_callback, (InviteMemberEvent,))
        self.client.add_to_device_callback(
            self.to_device_callback, (KeyVerificationEvent,)
        )

        # regular expression to match keyword commands
        self.gpt_prog = re.compile(r"^\s*!gpt\s*(.+)$")
        self.chat_prog = re.compile(r"^\s*!chat\s*(.+)$")
        self.pic_prog = re.compile(r"^\s*!pic\s*(.+)$")
        self.lc_prog = re.compile(r"^\s*!lc\s*(.+)$")
        self.help_prog = re.compile(r"^\s*!help\s*.*$")
        self.new_prog = re.compile(r"^\s*!new\s*(.+)$")

    async def close(self, task: asyncio.Task) -> None:
        await self.httpx_client.aclose()
        await self.client.close()
        task.cancel()
        logger.info("Bot closed!")

    # message_callback RoomMessageText event
    async def message_callback(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self.room_id is None:
            room_id = room.room_id
        else:
            # if event room id does not match the room id in config, return
            if room.room_id != self.room_id:
                return
            room_id = self.room_id

        # reply event_id
        reply_to_event_id = event.event_id

        # sender_id
        sender_id = event.sender

        # user_message
        raw_user_message = event.body

        # print info to console
        logger.info(
            f"Message received in room {room.display_name}\n"
            f"{room.user_name(event.sender)} | {raw_user_message}"
        )

        # prevent command trigger loop
        if self.user_id != event.sender:
            # remove newline character from event.body
            content_body = re.sub("\r\n|\r|\n", " ", raw_user_message)

            # !gpt command
            if self.openai_api_key is not None:
                m = self.gpt_prog.match(content_body)
                if m:
                    prompt = m.group(1)
                    try:
                        asyncio.create_task(
                            self.gpt(
                                room_id,
                                reply_to_event_id,
                                prompt,
                                sender_id,
                                raw_user_message,
                            )
                        )
                    except Exception as e:
                        logger.error(e, exc_info=True)

            if self.gpt_api_endpoint is not None:
                # chatgpt
                n = self.chat_prog.match(content_body)
                if n:
                    prompt = n.group(1)
                    if self.openai_api_key is not None:
                        try:
                            asyncio.create_task(
                                self.chat(
                                    room_id,
                                    reply_to_event_id,
                                    prompt,
                                    sender_id,
                                    raw_user_message,
                                )
                            )
                        except Exception as e:
                            logger.error(e, exc_info=True)
                    else:
                        logger.warning("No API_KEY provided")
                        await send_room_message(
                            self.client, room_id, reply_message="API_KEY not provided"
                        )

            # lc command
            if self.flowise_api_url is not None:
                m = self.lc_prog.match(content_body)
                if m:
                    prompt = m.group(1)
                    try:
                        asyncio.create_task(
                            self.lc(
                                room_id,
                                reply_to_event_id,
                                prompt,
                                sender_id,
                                raw_user_message,
                            )
                        )
                    except Exception as e:
                        await send_room_message(self.client, room_id, reply_message={e})
                        logger.error(e, exc_info=True)

            # !new command
            n = self.new_prog.match(content_body)
            if n:
                new_command = n.group(1)
                try:
                    asyncio.create_task(
                        self.new(
                            room_id,
                            reply_to_event_id,
                            sender_id,
                            raw_user_message,
                            new_command,
                        )
                    )
                except Exception as e:
                    logger.error(e, exc_info=True)

            # help command
            h = self.help_prog.match(content_body)
            if h:
                try:
                    asyncio.create_task(
                        self.help(
                            room_id, reply_to_event_id, sender_id, raw_user_message
                        )
                    )
                except Exception as e:
                    logger.error(e, exc_info=True)

    # message_callback decryption_failure event
    async def decryption_failure(self, room: MatrixRoom, event: MegolmEvent) -> None:
        if not isinstance(event, MegolmEvent):
            return

        logger.error(
            f"Failed to decrypt message: {event.event_id} \
                from {event.sender} in {room.room_id}\n"
            + "Please make sure the bot current session is verified"
        )

    # invite_callback event
    async def invite_callback(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        """Handle an incoming invite event.
        If an invite is received, then join the room specified in the invite.
        code copied from: https://github.com/8go/matrix-eno-bot/blob/ad037e02bd2960941109e9526c1033dd157bb212/callbacks.py#L104
        """
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")
        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                break
        else:
            logger.error("Unable to join room: %s", room.room_id)

        # Successfully joined room
        logger.info(f"Joined {room.room_id}")

    # to_device_callback event
    async def to_device_callback(self, event: KeyVerificationEvent) -> None:
        """Handle events sent to device.

        Specifically this will perform Emoji verification.
        It will accept an incoming Emoji verification requests
        and follow the verification protocol.
        code copied from: https://github.com/8go/matrix-eno-bot/blob/ad037e02bd2960941109e9526c1033dd157bb212/callbacks.py#L127
        """
        try:
            client = self.client
            logger.debug(
                f"Device Event of type {type(event)} received in " "to_device_cb()."
            )

            if isinstance(event, KeyVerificationStart):  # first step
                """first step: receive KeyVerificationStart
                KeyVerificationStart(
                    source={'content':
                            {'method': 'm.sas.v1',
                             'from_device': 'DEVICEIDXY',
                             'key_agreement_protocols':
                                ['curve25519-hkdf-sha256', 'curve25519'],
                             'hashes': ['sha256'],
                             'message_authentication_codes':
                                ['hkdf-hmac-sha256', 'hmac-sha256'],
                             'short_authentication_string':
                                ['decimal', 'emoji'],
                             'transaction_id': 'SomeTxId'
                             },
                            'type': 'm.key.verification.start',
                            'sender': '@user2:example.org'
                            },
                    sender='@user2:example.org',
                    transaction_id='SomeTxId',
                    from_device='DEVICEIDXY',
                    method='m.sas.v1',
                    key_agreement_protocols=[
                        'curve25519-hkdf-sha256', 'curve25519'],
                    hashes=['sha256'],
                    message_authentication_codes=[
                        'hkdf-hmac-sha256', 'hmac-sha256'],
                    short_authentication_string=['decimal', 'emoji'])
                """

                if "emoji" not in event.short_authentication_string:
                    estr = (
                        "Other device does not support emoji verification "
                        f"{event.short_authentication_string}. Aborting."
                    )
                    logger.info(estr)
                    return
                resp = await client.accept_key_verification(event.transaction_id)
                if isinstance(resp, ToDeviceError):
                    estr = f"accept_key_verification() failed with {resp}"
                    logger.info(estr)

                sas = client.key_verifications[event.transaction_id]

                todevice_msg = sas.share_key()
                resp = await client.to_device(todevice_msg)
                if isinstance(resp, ToDeviceError):
                    estr = f"to_device() failed with {resp}"
                    logger.info(estr)

            elif isinstance(event, KeyVerificationCancel):  # anytime
                """at any time: receive KeyVerificationCancel
                KeyVerificationCancel(source={
                    'content': {'code': 'm.mismatched_sas',
                                'reason': 'Mismatched authentication string',
                                'transaction_id': 'SomeTxId'},
                    'type': 'm.key.verification.cancel',
                    'sender': '@user2:example.org'},
                    sender='@user2:example.org',
                    transaction_id='SomeTxId',
                    code='m.mismatched_sas',
                    reason='Mismatched short authentication string')
                """

                # There is no need to issue a
                # client.cancel_key_verification(tx_id, reject=False)
                # here. The SAS flow is already cancelled.
                # We only need to inform the user.
                estr = (
                    f"Verification has been cancelled by {event.sender} "
                    f'for reason "{event.reason}".'
                )
                logger.info(estr)

            elif isinstance(event, KeyVerificationKey):  # second step
                """Second step is to receive KeyVerificationKey
                KeyVerificationKey(
                    source={'content': {
                            'key': 'SomeCryptoKey',
                            'transaction_id': 'SomeTxId'},
                        'type': 'm.key.verification.key',
                        'sender': '@user2:example.org'
                    },
                    sender='@user2:example.org',
                    transaction_id='SomeTxId',
                    key='SomeCryptoKey')
                """
                sas = client.key_verifications[event.transaction_id]

                logger.info(f"{sas.get_emoji()}")
                # don't log the emojis

                # The bot process must run in forground with a screen and
                # keyboard so that user can accept/reject via keyboard.
                # For emoji verification bot must not run as service or
                # in background.
                # yn = input("Do the emojis match? (Y/N) (C for Cancel) ")
                # automatic match, so we use y
                yn = "y"
                if yn.lower() == "y":
                    estr = (
                        "Match! The verification for this " "device will be accepted."
                    )
                    logger.info(estr)
                    resp = await client.confirm_short_auth_string(event.transaction_id)
                    if isinstance(resp, ToDeviceError):
                        estr = "confirm_short_auth_string() " f"failed with {resp}"
                        logger.info(estr)
                elif yn.lower() == "n":  # no, don't match, reject
                    estr = (
                        "No match! Device will NOT be verified "
                        "by rejecting verification."
                    )
                    logger.info(estr)
                    resp = await client.cancel_key_verification(
                        event.transaction_id, reject=True
                    )
                    if isinstance(resp, ToDeviceError):
                        estr = f"cancel_key_verification failed with {resp}"
                        logger.info(estr)
                else:  # C or anything for cancel
                    estr = "Cancelled by user! Verification will be " "cancelled."
                    logger.info(estr)
                    resp = await client.cancel_key_verification(
                        event.transaction_id, reject=False
                    )
                    if isinstance(resp, ToDeviceError):
                        estr = f"cancel_key_verification failed with {resp}"
                        logger.info(estr)

            elif isinstance(event, KeyVerificationMac):  # third step
                """Third step is to receive KeyVerificationMac
                KeyVerificationMac(
                    source={'content': {
                        'mac': {'ed25519:DEVICEIDXY': 'SomeKey1',
                                'ed25519:SomeKey2': 'SomeKey3'},
                        'keys': 'SomeCryptoKey4',
                        'transaction_id': 'SomeTxId'},
                        'type': 'm.key.verification.mac',
                        'sender': '@user2:example.org'},
                    sender='@user2:example.org',
                    transaction_id='SomeTxId',
                    mac={'ed25519:DEVICEIDXY': 'SomeKey1',
                         'ed25519:SomeKey2': 'SomeKey3'},
                    keys='SomeCryptoKey4')
                """
                sas = client.key_verifications[event.transaction_id]
                try:
                    todevice_msg = sas.get_mac()
                except LocalProtocolError as e:
                    # e.g. it might have been cancelled by ourselves
                    estr = (
                        f"Cancelled or protocol error: Reason: {e}.\n"
                        f"Verification with {event.sender} not concluded. "
                        "Try again?"
                    )
                    logger.info(estr)
                else:
                    resp = await client.to_device(todevice_msg)
                    if isinstance(resp, ToDeviceError):
                        estr = f"to_device failed with {resp}"
                        logger.info(estr)
                    estr = (
                        f"sas.we_started_it = {sas.we_started_it}\n"
                        f"sas.sas_accepted = {sas.sas_accepted}\n"
                        f"sas.canceled = {sas.canceled}\n"
                        f"sas.timed_out = {sas.timed_out}\n"
                        f"sas.verified = {sas.verified}\n"
                        f"sas.verified_devices = {sas.verified_devices}\n"
                    )
                    logger.info(estr)
                    estr = (
                        "Emoji verification was successful!\n"
                        "Initiate another Emoji verification from "
                        "another device or room if desired. "
                        "Or if done verifying, hit Control-C to stop the "
                        "bot in order to restart it as a service or to "
                        "run it in the background."
                    )
                    logger.info(estr)
            else:
                estr = (
                    f"Received unexpected event type {type(event)}. "
                    f"Event is {event}. Event will be ignored."
                )
                logger.info(estr)
        except BaseException:
            estr = traceback.format_exc()
            logger.info(estr)

    # !chat command
    async def chat(
        self, room_id, reply_to_event_id, prompt, sender_id, raw_user_message
    ):
        try:
            await self.client.room_typing(room_id, timeout=int(self.timeout) * 1000)
            content = await self.chatbot.ask_async(
                prompt=prompt,
                convo_id=sender_id,
            )
            await send_room_message(
                self.client,
                room_id,
                reply_message=content,
                reply_to_event_id=reply_to_event_id,
                sender_id=sender_id,
                user_message=raw_user_message,
            )
        except Exception:
            await self.send_general_error_message(
                room_id, reply_to_event_id, sender_id, raw_user_message
            )

    # !gpt command
    async def gpt(
        self, room_id, reply_to_event_id, prompt, sender_id, raw_user_message
    ) -> None:
        try:
            # sending typing state, seconds to milliseconds
            await self.client.room_typing(room_id, timeout=int(self.timeout) * 1000)
            responseMessage = await self.chatbot.oneTimeAsk(
                prompt=prompt,
            )

            await send_room_message(
                self.client,
                room_id,
                reply_message=responseMessage.strip(),
                reply_to_event_id=reply_to_event_id,
                sender_id=sender_id,
                user_message=raw_user_message,
            )
        except Exception:
            await self.send_general_error_message(
                room_id, reply_to_event_id, sender_id, raw_user_message
            )

    # !lc command
    async def lc(
        self, room_id, reply_to_event_id, prompt, sender_id, raw_user_message
    ) -> None:
        try:
            # sending typing state
            await self.client.room_typing(room_id, timeout=int(self.timeout) * 1000)
            if self.flowise_api_key is not None:
                headers = {"Authorization": f"Bearer {self.flowise_api_key}"}
                responseMessage = await flowise_query(
                    self.flowise_api_url, prompt, self.httpx_client, headers
                )
            else:
                responseMessage = await flowise_query(
                    self.flowise_api_url, prompt, self.httpx_client
                )
            await send_room_message(
                self.client,
                room_id,
                reply_message=responseMessage.strip(),
                reply_to_event_id=reply_to_event_id,
                sender_id=sender_id,
                user_message=raw_user_message,
            )
        except Exception:
            await self.send_general_error_message(
                room_id, reply_to_event_id, sender_id, raw_user_message
            )

    # !new command
    async def new(
        self,
        room_id,
        reply_to_event_id,
        sender_id,
        raw_user_message,
        new_command,
    ) -> None:
        try:
            if "chat" in new_command:
                self.chatbot.reset(convo_id=sender_id)
                content = (
                    "New conversation created, please use !chat to start chatting!"
                )
            else:
                content = "Unkown keyword, please use !help to get available commands"

            await send_room_message(
                self.client,
                room_id,
                reply_message=content,
                reply_to_event_id=reply_to_event_id,
                sender_id=sender_id,
                user_message=raw_user_message,
            )
        except Exception:
            await self.send_general_error_message(
                room_id, reply_to_event_id, sender_id, raw_user_message
            )

    # !pic command
    async def pic(self, room_id, prompt, replay_to_event_id):
        try:
            await self.client.room_typing(room_id, timeout=int(self.timeout) * 1000)
            # generate image
            links = await self.imageGen.get_images(prompt)
            image_path_list = await self.imageGen.save_images(
                links, self.base_path / "images", self.output_four_images
            )
            # send image
            for image_path in image_path_list:
                await send_room_image(self.client, room_id, image_path)
            await self.client.room_typing(room_id, typing_state=False)
        except Exception as e:
            await send_room_message(
                self.client,
                room_id,
                reply_message=str(e),
                reply_to_event_id=replay_to_event_id,
            )

    # !help command
    async def help(self, room_id, reply_to_event_id, sender_id, user_message):
        help_info = (
            "!gpt [prompt], generate a one time response without context conversation\n"
            + "!chat [prompt], chat with context conversation\n"
            + "!pic [prompt], Image generation by Microsoft Bing\n"
            + "!new + chat, start a new conversation \n"
            + "!lc [prompt], chat using langchain api\n"
            + "!help, help message"
        )  # noqa: E501

        await send_room_message(
            self.client,
            room_id,
            reply_message=help_info,
            sender_id=sender_id,
            user_message=user_message,
            reply_to_event_id=reply_to_event_id,
        )

    # send general error message
    async def send_general_error_message(
        self, room_id, reply_to_event_id, sender_id, user_message
    ):
        await send_room_message(
            self.client,
            room_id,
            reply_message=GENERAL_ERROR_MESSAGE,
            reply_to_event_id=reply_to_event_id,
            sender_id=sender_id,
            user_message=user_message,
        )

    # bot login
    async def login(self) -> None:
        resp = await self.client.login(password=self.password, device_name=DEVICE_NAME)
        if not isinstance(resp, LoginResponse):
            logger.error("Login Failed")
            await self.httpx_client.aclose()
            await self.client.close()
            sys.exit(1)
        logger.info("Success login via password")

    # import keys
    async def import_keys(self):
        resp = await self.client.import_keys(
            self.import_keys_path, self.import_keys_password
        )
        if isinstance(resp, EncryptionError):
            logger.error(f"import_keys failed with {resp}")
        else:
            logger.info(
                "import_keys success, please remove import_keys configuration!!!"
            )

    # sync messages in the room
    async def sync_forever(self, timeout=30000, full_state=True) -> None:
        await self.client.sync_forever(timeout=timeout, full_state=full_state)