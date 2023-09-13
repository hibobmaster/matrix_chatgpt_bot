## Introduction

This is a simple Matrix bot that support using OpenAI API, Langchain to generate responses from user inputs. The bot responds to these commands: `!gpt`, `!chat` and `!pic` and `!talk`, `!goon`, `!new` and `!lc` and `!help` depending on the first word of the prompt.
![ChatGPT](https://i.imgur.com/kK4rnPf.jpeg)

## Feature

1. Support official openai api and self host models([LocalAI](https://github.com/go-skynet/LocalAI))   
2. Support E2E Encrypted Room
3. Colorful code blocks
4. Langchain([Flowise](https://github.com/FlowiseAI/Flowise))


## Installation and Setup

Docker method(Recommended):<br>
Edit `config.json` or `.env` with proper values <br>
For explainations and complete parameter list see: https://github.com/hibobmaster/matrix_chatgpt_bot/wiki <br>
Create two empty file, for persist database only<br>

```bash
touch sync_db manage_db
sudo docker compose up -d
```

<hr>
Normal Method:<br>
system dependece: <code>libolm-dev</code>

1. Clone the repository and create virtual environment:

```
git clone https://github.com/hibobmaster/matrix_chatgpt_bot.git

python -m venv venv
source venv/bin/activate
```

2. Install the required dependencies:<br>

```
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

3. Create a new config.json file and complete it with the necessary information:<br>
   Use password to login(recommended) or provide `access_token` <br>
   If not set:<br>
   `room_id`: bot will work in the room where it is in <br>
   `openai_api_key`: `!gpt` `!chat` command will not work <br>
   `api_endpoint`: `!bing` `!chat` command will not work <br>
   `bing_auth_cookie`: `!pic` command will not work

```json
{
  "homeserver": "YOUR_HOMESERVER",
  "user_id": "YOUR_USER_ID",
  "password": "YOUR_PASSWORD",
  "device_id": "YOUR_DEVICE_ID",
  "room_id": "YOUR_ROOM_ID",
  "openai_api_key": "YOUR_API_KEY",
  "api_endpoint": "xxxxxxxxx"
}
```

4. Launch the bot:

```
python src/main.py
```

## Usage

To interact with the bot, simply send a message to the bot in the Matrix room with one of the two prompts:<br>
- `!help` help message

- `!gpt` To generate a one time response:

```
!gpt What is the meaning of life?
```

- `!chat` To chat using official api with context conversation

```
!chat Can you tell me a joke?
```

- `!lc` To chat using langchain api endpoint
```
!lc All the world is a stage
```
- `!pic` To generate an image using openai DALL·E or LocalAI

```
!pic A bridal bouquet made of succulents
```
- `!new + {chat}` Start a new converstaion


## Image Generation


https://github.com/hibobmaster/matrix_chatgpt_bot/wiki/ <br>


## Thanks
1. [matrix-nio](https://github.com/poljar/matrix-nio)
2. [acheong08](https://github.com/acheong08)
3. [node-chatgpt-api](https://github.com/waylaidwanderer/node-chatgpt-api)
4. [8go](https://github.com/8go/)

<a href="https://jb.gg/OpenSourceSupport" target="_blank">
<img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" alt="JetBrains Logo (Main) logo." width="200" height="200">
</a>
