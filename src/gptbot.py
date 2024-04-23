"""
Code derived from https://github.com/acheong08/ChatGPT/blob/main/src/revChatGPT/V3.py
A simple wrapper for the official ChatGPT API
"""
import sqlite3
import json
from typing import AsyncGenerator
from tenacity import retry, wait_random_exponential, stop_after_attempt
import httpx
import tiktoken


ENGINES = ["gpt-3.5-turbo", "gpt-4", "gpt-4-32k", "gpt-4-turbo"]


class Chatbot:
    """
    Official ChatGPT API
    """

    def __init__(
        self,
        aclient: httpx.AsyncClient,
        api_key: str,
        api_url: str = None,
        engine: str = None,
        timeout: float = None,
        max_tokens: int = None,
        temperature: float = 0.8,
        top_p: float = 1.0,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        reply_count: int = 1,
        truncate_limit: int = None,
        system_prompt: str = None,
        db_path: str = "context.db",
    ) -> None:
        """
        Initialize Chatbot with API key (from https://platform.openai.com/account/api-keys)
        """
        self.engine: str = engine or "gpt-3.5-turbo"
        self.api_key: str = api_key
        self.api_url: str = api_url or "https://api.openai.com/v1/chat/completions"
        self.system_prompt: str = (
            system_prompt
            or "You are ChatGPT, \
            a large language model trained by OpenAI. Respond conversationally"
        )
        # https://platform.openai.com/docs/models
        self.max_tokens: int = max_tokens or (
            127000
            if "gpt-4-turbo" in engine
            else 31000
            if "gpt-4-32k" in engine
            else 7000
            if "gpt-4" in engine
            else 16000
        )
        self.truncate_limit: int = truncate_limit or (
            126500
            if "gpt-4-turbo" in engine
            else 30500
            if "gpt-4-32k" in engine
            else 6500
            if "gpt-4" in engine
            else 15500
        )
        self.temperature: float = temperature
        self.top_p: float = top_p
        self.presence_penalty: float = presence_penalty
        self.frequency_penalty: float = frequency_penalty
        self.reply_count: int = reply_count
        self.timeout: float = timeout

        self.aclient = aclient

        self.db_path = db_path

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        self._create_tables()

        self.conversation = self._load_conversation()

        if self.get_token_count("default") > self.max_tokens:
            raise Exception("System prompt is too long")

    def _create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    convo_id TEXT UNIQUE,
                    messages TEXT
            )
        """
        )

    def _load_conversation(self) -> dict[str, list[dict]]:
        conversations: dict[str, list[dict]] = {
            "default": [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
            ],
        }
        self.cursor.execute("SELECT convo_id, messages FROM conversations")
        for convo_id, messages in self.cursor.fetchall():
            conversations[convo_id] = json.loads(messages)
        return conversations

    def _save_conversation(self, convo_id) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO conversations (convo_id, messages) VALUES (?, ?)",
            (convo_id, json.dumps(self.conversation[convo_id])),
        )
        self.conn.commit()

    def add_to_conversation(
        self,
        message: str,
        role: str,
        convo_id: str = "default",
    ) -> None:
        """
        Add a message to the conversation
        """
        self.conversation[convo_id].append({"role": role, "content": message})
        self._save_conversation(convo_id)

    def __truncate_conversation(self, convo_id: str = "default") -> None:
        """
        Truncate the conversation
        """
        while True:
            if (
                self.get_token_count(convo_id) > self.truncate_limit
                and len(self.conversation[convo_id]) > 1
            ):
                # Don't remove the first message
                self.conversation[convo_id].pop(1)
            else:
                break
        self._save_conversation(convo_id)

    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def get_token_count(self, convo_id: str = "default") -> int:
        """
        Get token count
        """
        _engine = self.engine
        if self.engine not in ENGINES:
            # use gpt-3.5-turbo to caculate token
            _engine = "gpt-3.5-turbo"
        tiktoken.model.MODEL_TO_ENCODING["gpt-4"] = "cl100k_base"

        encoding = tiktoken.encoding_for_model(_engine)

        num_tokens = 0
        for message in self.conversation[convo_id]:
            # every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 5
            for key, value in message.items():
                if value:
                    num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += 5  # role is always required and always 1 token
        num_tokens += 5  # every reply is primed with <im_start>assistant
        return num_tokens

    def get_max_tokens(self, convo_id: str) -> int:
        """
        Get max tokens
        """
        return self.max_tokens - self.get_token_count(convo_id)

    async def ask_stream_async(
        self,
        prompt: str,
        role: str = "user",
        convo_id: str = "default",
        model: str = None,
        pass_history: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Ask a question
        """
        # Make conversation if it doesn't exist
        if convo_id not in self.conversation:
            self.reset(convo_id=convo_id, system_prompt=self.system_prompt)
        self.add_to_conversation(prompt, "user", convo_id=convo_id)
        self.__truncate_conversation(convo_id=convo_id)
        # Get response
        async with self.aclient.stream(
            "post",
            self.api_url,
            headers={"Authorization": f"Bearer {kwargs.get('api_key', self.api_key)}"},
            json={
                "model": model or self.engine,
                "messages": self.conversation[convo_id] if pass_history else [prompt],
                "stream": True,
                # kwargs
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "presence_penalty": kwargs.get(
                    "presence_penalty",
                    self.presence_penalty,
                ),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty",
                    self.frequency_penalty,
                ),
                "n": kwargs.get("n", self.reply_count),
                "user": role,
                "max_tokens": min(
                    self.get_max_tokens(convo_id=convo_id),
                    kwargs.get("max_tokens", self.max_tokens),
                ),
            },
            timeout=kwargs.get("timeout", self.timeout),
        ) as response:
            if response.status_code != 200:
                await response.aread()
                raise Exception(
                    f"{response.status_code} {response.reason_phrase} {response.text}",
                )

            response_role: str = ""
            full_response: str = ""
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                # Remove "data: "
                line = line[6:]
                if line == "[DONE]":
                    break
                resp: dict = json.loads(line)
                if "error" in resp:
                    raise Exception(f"{resp['error']}")
                choices = resp.get("choices")
                if not choices:
                    continue
                delta: dict[str, str] = choices[0].get("delta")
                if not delta:
                    continue
                if "role" in delta:
                    response_role = delta["role"]
                if "content" in delta:
                    content: str = delta["content"]
                    full_response += content
                    yield content
        self.add_to_conversation(full_response, response_role, convo_id=convo_id)

    async def ask_async(
        self,
        prompt: str,
        role: str = "user",
        convo_id: str = "default",
        model: str = None,
        pass_history: bool = True,
        **kwargs,
    ) -> str:
        """
        Non-streaming ask
        """
        response = self.ask_stream_async(
            prompt=prompt,
            role=role,
            convo_id=convo_id,
            model=model,
            pass_history=pass_history,
            **kwargs,
        )
        full_response: str = "".join([r async for r in response])
        return full_response

    async def ask_async_v2(
        self,
        prompt: str,
        role: str = "user",
        convo_id: str = "default",
        model: str = None,
        pass_history: bool = True,
        **kwargs,
    ) -> str:
        # Make conversation if it doesn't exist
        if convo_id not in self.conversation:
            self.reset(convo_id=convo_id, system_prompt=self.system_prompt)
        self.add_to_conversation(prompt, "user", convo_id=convo_id)
        self.__truncate_conversation(convo_id=convo_id)
        # Get response
        response = await self.aclient.post(
            url=self.api_url,
            headers={"Authorization": f"Bearer {kwargs.get('api_key', self.api_key)}"},
            json={
                "model": model or self.engine,
                "messages": self.conversation[convo_id] if pass_history else [prompt],
                # kwargs
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "presence_penalty": kwargs.get(
                    "presence_penalty",
                    self.presence_penalty,
                ),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty",
                    self.frequency_penalty,
                ),
                "n": kwargs.get("n", self.reply_count),
                "user": role,
                "max_tokens": min(
                    self.get_max_tokens(convo_id=convo_id),
                    kwargs.get("max_tokens", self.max_tokens),
                ),
            },
            timeout=kwargs.get("timeout", self.timeout),
        )
        resp = response.json()
        full_response = resp["choices"][0]["message"]["content"]
        self.add_to_conversation(
            full_response, resp["choices"][0]["message"]["role"], convo_id=convo_id
        )
        return full_response

    def reset(self, convo_id: str = "default", system_prompt: str = None) -> None:
        """
        Reset the conversation
        """
        self.conversation[convo_id] = [
            {"role": "system", "content": system_prompt or self.system_prompt},
        ]
        self._save_conversation(convo_id)

    @retry(wait=wait_random_exponential(min=2, max=5), stop=stop_after_attempt(3))
    async def oneTimeAsk(
        self,
        prompt: str,
        role: str = "user",
        model: str = None,
        **kwargs,
    ) -> str:
        response = await self.aclient.post(
            url=self.api_url,
            json={
                "model": model or self.engine,
                "messages": [
                    {
                        "role": role,
                        "content": prompt,
                    }
                ],
                # kwargs
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "presence_penalty": kwargs.get(
                    "presence_penalty",
                    self.presence_penalty,
                ),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty",
                    self.frequency_penalty,
                ),
                "user": role,
            },
            headers={"Authorization": f"Bearer {kwargs.get('api_key', self.api_key)}"},
            timeout=kwargs.get("timeout", self.timeout),
        )
        resp = response.json()
        return resp["choices"][0]["message"]["content"]
