import asyncio
import os
import re
import sys
import traceback
from typing import Union, Optional

import aiohttp
from nio import (AsyncClient, AsyncClientConfig, InviteMemberEvent, JoinError,
                 KeyVerificationCancel, KeyVerificationEvent, EncryptionError,
                 KeyVerificationKey, KeyVerificationMac, KeyVerificationStart,
                 LocalProtocolError, LoginResponse, MatrixRoom, MegolmEvent,
                 RoomMessageText, ToDeviceError)
from nio.store.database import SqliteStore

from askgpt import askGPT
from bing import BingBot
from BingImageGen import ImageGenAsync
from log import getlogger
from send_image import send_room_image
from send_message import send_room_message
from v3 import Chatbot
from bard import Bardbot
from flowise import flowise_query

logger = getlogger()


class Bot:
    def __init__(
        self,
        homeserver: str,
        user_id: str,
        device_id: str,
        chatgpt_api_endpoint: str = os.environ.get(
            "CHATGPT_API_ENDPOINT") or "https://api.openai.com/v1/chat/completions",
        api_key: Union[str, None] = None,
        room_id: Union[str, None] = None,
        bing_api_endpoint: Union[str, None] = None,
        password: Union[str, None] = None,
        access_token: Union[str, None] = None,
        bard_token: Union[str, None] = None,
        jailbreakEnabled: Union[bool, None] = True,
        bing_auth_cookie: Union[str, None] = '',
        markdown_formatted: Union[bool, None] = False,
        output_four_images: Union[bool, None] = False,
        import_keys_path: Optional[str] = None,
        import_keys_password: Optional[str] = None,
        flowise_api_url: Optional[str] = None,
        flowise_api_key: Optional[str] = None
    ):
        if (homeserver is None or user_id is None
                or device_id is None):
            logger.warning("homeserver && user_id && device_id is required")
            sys.exit(1)

        if (password is None and access_token is None):
            logger.warning("password or access_toekn is required")
            sys.exit(1)

        self.homeserver = homeserver
        self.user_id = user_id
        self.password = password
        self.access_token = access_token
        self.bard_token = bard_token
        self.device_id = device_id
        self.room_id = room_id
        self.api_key = api_key
        self.chatgpt_api_endpoint = chatgpt_api_endpoint
        self.import_keys_path = import_keys_path
        self.import_keys_password = import_keys_password
        self.flowise_api_url = flowise_api_url
        self.flowise_api_key = flowise_api_key

        self.session = aiohttp.ClientSession()

        if bing_api_endpoint is None:
            self.bing_api_endpoint = ''
        else:
            self.bing_api_endpoint = bing_api_endpoint

        if jailbreakEnabled is None:
            self.jailbreakEnabled = True
        else:
            self.jailbreakEnabled = jailbreakEnabled

        if bing_auth_cookie is None:
            self.bing_auth_cookie = ''
        else:
            self.bing_auth_cookie = bing_auth_cookie

        if markdown_formatted is None:
            self.markdown_formatted = False
        else:
            self.markdown_formatted = markdown_formatted

        if output_four_images is None:
            self.output_four_images = False
        else:
            self.output_four_images = output_four_images

        # initialize AsyncClient object
        self.store_path = os.getcwd()
        self.config = AsyncClientConfig(store=SqliteStore,
                                        store_name="db",
                                        store_sync_tokens=True,
                                        encryption_enabled=True,
                                        )
        self.client = AsyncClient(homeserver=self.homeserver, user=self.user_id,
                                  device_id=self.device_id,
                                  config=self.config, store_path=self.store_path,)

        if self.access_token is not None:
            self.client.access_token = self.access_token

        # setup event callbacks
        self.client.add_event_callback(
            self.message_callback, (RoomMessageText, ))
        self.client.add_event_callback(
            self.decryption_failure, (MegolmEvent, ))
        self.client.add_event_callback(
            self.invite_callback, (InviteMemberEvent, ))
        self.client.add_to_device_callback(
            self.to_device_callback, (KeyVerificationEvent, ))

        # regular expression to match keyword commands
        self.gpt_prog = re.compile(r"^\s*!gpt\s*(.+)$")
        self.chat_prog = re.compile(r"^\s*!chat\s*(.+)$")
        self.bing_prog = re.compile(r"^\s*!bing\s*(.+)$")
        self.bard_prog = re.compile(r"^\s*!bard\s*(.+)$")
        self.pic_prog = re.compile(r"^\s*!pic\s*(.+)$")
        self.lc_prog = re.compile(r"^\s*!lc\s*(.+)$")
        self.help_prog = re.compile(r"^\s*!help\s*.*$")

        # initialize chatbot and chatgpt_api_endpoint
        if self.api_key is not None:
            self.chatbot = Chatbot(api_key=self.api_key, timeout=120)

            self.chatgpt_api_endpoint = self.chatgpt_api_endpoint
            # request header for !gpt command
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

        # initialize askGPT class
        self.askgpt = askGPT(self.session)

        # initialize bingbot
        if self.bing_api_endpoint != '':
            self.bingbot = BingBot(
                self.session, bing_api_endpoint, jailbreakEnabled=self.jailbreakEnabled)

        # initialize BingImageGenAsync
        if self.bing_auth_cookie != '':
            self.imageGen = ImageGenAsync(self.bing_auth_cookie, quiet=True)

        # initialize Bardbot
        if bard_token is not None:
            self.bardbot = Bardbot(self.bard_token)

    def __del__(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._close())

    async def _close(self):
        await self.session.close()

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

            # chatgpt
            n = self.chat_prog.match(content_body)
            if n:
                prompt = n.group(1)
                if self.api_key is not None:
                    try:
                        asyncio.create_task(self.chat(room_id,
                                                      reply_to_event_id,
                                                      prompt,
                                                      sender_id,
                                                      raw_user_message
                                                      )
                                            )
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        await send_room_message(self.client, room_id,
                                                reply_message=str(e))
                else:
                    logger.warning("No API_KEY provided")
                    await send_room_message(self.client, room_id,
                                            reply_message="API_KEY not provided")

            m = self.gpt_prog.match(content_body)
            if m:
                prompt = m.group(1)
                try:
                    asyncio.create_task(self.gpt(
                        room_id,
                        reply_to_event_id,
                        prompt, sender_id,
                        raw_user_message
                    )
                    )
                except Exception as e:
                    logger.error(e, exc_info=True)
                    await send_room_message(self.client, room_id, reply_message=str(e))

            # bing ai
            if self.bing_api_endpoint != '':
                b = self.bing_prog.match(content_body)
                if b:
                    prompt = b.group(1)
                    # raw_content_body used for construct formatted_body
                    try:
                        asyncio.create_task(self.bing(
                            room_id,
                            reply_to_event_id,
                            prompt,
                            sender_id,
                            raw_user_message
                        )
                        )
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        await send_room_message(self.client, room_id,
                                                reply_message=str(e))

            # Image Generation by Microsoft Bing
            if self.bing_auth_cookie != '':
                i = self.pic_prog.match(content_body)
                if i:
                    prompt = i.group(1)
                    try:
                        asyncio.create_task(self.pic(room_id, prompt))
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        await send_room_message(self.client, room_id,
                                                reply_message=str(e))

            # Google's Bard
            if self.bard_token is not None:
                b = self.bard_prog.match(content_body)
                if b:
                    prompt = b.group(1)
                    try:
                        asyncio.create_task(self.bard(
                            room_id,
                            reply_to_event_id,
                            prompt,
                            sender_id,
                            raw_user_message
                        )
                        )
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        await send_room_message(self.client, room_id, reply_message={e})

            # lc command
            if self.flowise_api_url is not None:
                m = self.lc_prog.match(content_body)
                if m:
                    prompt = m.group(1)
                    try:
                        asyncio.create_task(self.lc(
                            room_id,
                            reply_to_event_id,
                            prompt,
                            sender_id,
                            raw_user_message
                        )
                        )
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        await send_room_message(self.client, room_id, reply_message={e})

            # help command
            h = self.help_prog.match(content_body)
            if h:
                asyncio.create_task(self.help(room_id))

    # message_callback decryption_failure event
    async def decryption_failure(self, room: MatrixRoom, event: MegolmEvent) -> None:
        if not isinstance(event, MegolmEvent):
            return

        logger.error(
            f"Failed to decrypt message: {event.event_id} \
                from {event.sender} in {room.room_id}\n" +
            "Please make sure the bot current session is verified"
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
                    attempt, result.message,
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
                f"Device Event of type {type(event)} received in "
                "to_device_cb().")

            if isinstance(event, KeyVerificationStart):  # first step
                """ first step: receive KeyVerificationStart
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
                    estr = ("Other device does not support emoji verification "
                            f"{event.short_authentication_string}. Aborting.")
                    logger.info(estr)
                    return
                resp = await client.accept_key_verification(
                    event.transaction_id)
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
                """ at any time: receive KeyVerificationCancel
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
                estr = (f"Verification has been cancelled by {event.sender} "
                        f"for reason \"{event.reason}\".")
                logger.info(estr)

            elif isinstance(event, KeyVerificationKey):  # second step
                """ Second step is to receive KeyVerificationKey
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
                    estr = ("Match! The verification for this "
                            "device will be accepted.")
                    logger.info(estr)
                    resp = await client.confirm_short_auth_string(
                        event.transaction_id)
                    if isinstance(resp, ToDeviceError):
                        estr = ("confirm_short_auth_string() "
                                f"failed with {resp}")
                        logger.info(estr)
                elif yn.lower() == "n":  # no, don't match, reject
                    estr = ("No match! Device will NOT be verified "
                            "by rejecting verification.")
                    logger.info(estr)
                    resp = await client.cancel_key_verification(
                        event.transaction_id, reject=True)
                    if isinstance(resp, ToDeviceError):
                        estr = (f"cancel_key_verification failed with {resp}")
                        logger.info(estr)
                else:  # C or anything for cancel
                    estr = ("Cancelled by user! Verification will be "
                            "cancelled.")
                    logger.info(estr)
                    resp = await client.cancel_key_verification(
                        event.transaction_id, reject=False)
                    if isinstance(resp, ToDeviceError):
                        estr = (f"cancel_key_verification failed with {resp}")
                        logger.info(estr)

            elif isinstance(event, KeyVerificationMac):  # third step
                """ Third step is to receive KeyVerificationMac
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
                    estr = (f"Cancelled or protocol error: Reason: {e}.\n"
                            f"Verification with {event.sender} not concluded. "
                            "Try again?")
                    logger.info(estr)
                else:
                    resp = await client.to_device(todevice_msg)
                    if isinstance(resp, ToDeviceError):
                        estr = f"to_device failed with {resp}"
                        logger.info(estr)
                    estr = (f"sas.we_started_it = {sas.we_started_it}\n"
                            f"sas.sas_accepted = {sas.sas_accepted}\n"
                            f"sas.canceled = {sas.canceled}\n"
                            f"sas.timed_out = {sas.timed_out}\n"
                            f"sas.verified = {sas.verified}\n"
                            f"sas.verified_devices = {sas.verified_devices}\n")
                    logger.info(estr)
                    estr = ("Emoji verification was successful!\n"
                            "Initiate another Emoji verification from "
                            "another device or room if desired. "
                            "Or if done verifying, hit Control-C to stop the "
                            "bot in order to restart it as a service or to "
                            "run it in the background.")
                    logger.info(estr)
            else:
                estr = (f"Received unexpected event type {type(event)}. "
                        f"Event is {event}. Event will be ignored.")
                logger.info(estr)
        except BaseException:
            estr = traceback.format_exc()
            logger.info(estr)

    # !chat command
    async def chat(self, room_id, reply_to_event_id, prompt, sender_id,
                   raw_user_message):
        await self.client.room_typing(room_id, timeout=120000)
        try:
            text = await self.chatbot.ask_async(prompt)
        except Exception as e:
            raise Exception(e)

        try:
            text = text.strip()
            await send_room_message(self.client, room_id, reply_message=text,
                                    reply_to_event_id="", sender_id=sender_id,
                                    user_message=raw_user_message,
                                    markdown_formatted=self.markdown_formatted)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # !gpt command
    async def gpt(self, room_id, reply_to_event_id, prompt, sender_id,
                  raw_user_message) -> None:
        try:
            # sending typing state
            await self.client.room_typing(room_id, timeout=240000)
            # timeout 240s
            text = await asyncio.wait_for(self.askgpt.oneTimeAsk(prompt,
                                                                 self.chatgpt_api_endpoint,
                                                                 self.headers),
                                                                 timeout=240)
        except TimeoutError:
            logger.error("TimeoutException", exc_info=True)
            raise Exception("Timeout error")
        except Exception as e:
            raise Exception(e)

        try:
            text = text.strip()
            await send_room_message(self.client, room_id, reply_message=text,
                                    reply_to_event_id="", sender_id=sender_id,
                                    user_message=raw_user_message,
                                    markdown_formatted=self.markdown_formatted)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)

    # !bing command
    async def bing(self, room_id, reply_to_event_id, prompt, sender_id,
                   raw_user_message) -> None:
        try:
            # sending typing state
            await self.client.room_typing(room_id, timeout=180000)
            # timeout 240s
            text = await asyncio.wait_for(self.bingbot.ask_bing(prompt), timeout=240)
        except TimeoutError:
            logger.error("timeoutException", exc_info=True)
            raise Exception("Timeout error")
        except Exception as e:
            raise Exception(e)

        try:
            text = text.strip()
            await send_room_message(self.client, room_id, reply_message=text,
                                    reply_to_event_id="", sender_id=sender_id,
                                    user_message=raw_user_message,
                                    markdown_formatted=self.markdown_formatted)
        except Exception as e:
            logger.error(e, exc_info=True)

    # !bard command
    async def bard(self, room_id, reply_to_event_id, prompt, sender_id,
                   raw_user_message) -> None:
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            response = await asyncio.to_thread(self.bardbot.ask, prompt)
        except Exception as e:
            raise Exception(e)

        try:
            content = str(response['content']).strip()
            await send_room_message(self.client, room_id, reply_message=content,
                                    reply_to_event_id="", sender_id=sender_id,
                                    user_message=raw_user_message,
                                    markdown_formatted=self.markdown_formatted)
        except Exception as e:
            logger.error(e, exc_info=True)

    # !lc command
    async def lc(self, room_id, reply_to_event_id, prompt, sender_id,
                raw_user_message) -> None:
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            if self.flowise_api_key is not None:
                headers = {'Authorization': f'Bearer {self.flowise_api_key}'}
                response = await asyncio.to_thread(flowise_query,
                                               self.flowise_api_url, prompt, headers)
            else:
                response = await asyncio.to_thread(flowise_query,
                                               self.flowise_api_url, prompt)
            await send_room_message(self.client, room_id, reply_message=response,
                                    reply_to_event_id="", sender_id=sender_id,
                                    user_message=raw_user_message,
                                    markdown_formatted=self.markdown_formatted)
        except Exception as e:
            raise Exception(e)

    # !pic command

    async def pic(self, room_id, prompt):
        try:
            await self.client.room_typing(room_id, timeout=180000)
            # generate image
            try:

                links = await self.imageGen.get_images(prompt)
                image_path_list = await self.imageGen.save_images(links, "images",
                                                             self.output_four_images)
            except Exception as e:
                logger.error(f"Image Generation error: {e}", exc_info=True)
                raise Exception(e)

            # send image
            try:
                for image_path in image_path_list:
                    await send_room_image(self.client, room_id, image_path)
                await self.client.room_typing(room_id, typing_state=False)
            except Exception as e:
                logger.error(e, exc_info=True)

        except Exception as e:
            logger.error(e, exc_info=True)

    # !help command
    async def help(self, room_id):
        try:
            # sending typing state
            await self.client.room_typing(room_id)
            help_info = "!gpt [prompt], generate response without context conversation\n" + \
                        "!chat [prompt], chat with context conversation\n" + \
                        "!bing [prompt], chat with context conversation powered by Bing AI\n" + \
                        "!bard [prompt], chat with Google's Bard\n" + \
                        "!pic [prompt], Image generation by Microsoft Bing\n" + \
                        "!lc [prompt], chat using langchain api\n" + \
                        "!help, help message"  # noqa: E501

            await send_room_message(self.client, room_id, reply_message=help_info)
        except Exception as e:
            logger.error(e, exc_info=True)

    # bot login
    async def login(self) -> None:
        if self.access_token is not None:
            logger.info("Login via access_token")
        else:
            logger.info("Login via password")
            try:
                resp = await self.client.login(password=self.password)
                if not isinstance(resp, LoginResponse):
                    logger.error("Login Failed")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)

    # import keys
    async def import_keys(self):
        resp = await self.client.import_keys(
            self.import_keys_path,
            self.import_keys_password
        )
        if isinstance(resp, EncryptionError):
            logger.error(f"import_keys failed with {resp}")
        else:
            logger.info(
                "import_keys success, please remove import_keys configuration!!!")

    # sync messages in the room
    async def sync_forever(self, timeout=30000, full_state=True) -> None:

        await self.client.sync_forever(timeout=timeout, full_state=full_state)
