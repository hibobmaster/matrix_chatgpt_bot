## Introduction

This is a simple Matrix bot that uses OpenAI's GPT API and Bing AI to generate responses to user inputs. The bot responds to five types of prompts: `!gpt`, `!chat` and `!bing` and `!pic` and `!bard` depending on the first word of the prompt.
![Bing](https://user-images.githubusercontent.com/32976627/231073146-3e380217-a6a2-413d-9203-ab36965b909d.png)
![Bard](https://i.imgur.com/OCXEuaa.png)
![ChatGPT](https://i.imgur.com/kK4rnPf.jpeg)

## Feature

1. Support Openai ChatGPT and Bing AI and Google Bard(US only at the moment)
2. Support Bing Image Creator
3. Support E2E Encrypted Room
4. Colorful code blocks

## Installation and Setup

Docker method(Recommended):<br>
Edit `config.json` or `.env` with proper values <br>
Create an empty file, for persist database only<br>

```bash
touch db
sudo docker compose up -d
```

<hr>
Normal Method:<br>

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

3. Create a new config.json file and fill it with the necessary information:<br>
   Use password to login(recommended) or provide `access_token` <br>
   If not set:<br>
   `room_id`: bot will work in the room where it is in <br>
   `api_key`: `!chat` command will not work <br>
   `bing_api_endpoint`: `!bing` command will not work <br>
   `bing_auth_cookie`: `!pic` command will not work

```json
{
  "homeserver": "YOUR_HOMESERVER",
  "user_id": "YOUR_USER_ID",
  "password": "YOUR_PASSWORD",
  "device_id": "YOUR_DEVICE_ID",
  "room_id": "YOUR_ROOM_ID",
  "api_key": "YOUR_API_KEY",
  "access_token": "xxxxxxxxxxxxxx",
  "bing_api_endpoint": "xxxxxxxxx",
  "bing_auth_cookie": "xxxxxxxxxx"
}
```

4. Start the bot:

```
python main.py
```

## Usage

To interact with the bot, simply send a message to the bot in the Matrix room with one of the two prompts:<br>

- `!gpt` To generate a one time response:

```
!gpt What is the meaning of life?
```

- `!chat` To chat using official api with context conversation

```
!chat Can you tell me a joke?
```

- `!bing` To chat with Bing AI with context conversation

```
!bing Do you know Victor Marie Hugo?
```

- `!bard` To chat with Google's Bard
```
!bard Building a website can be done in 10 simple steps
```

- `!pic` To generate an image from Microsoft Bing

```
!pic A bridal bouquet made of succulents
```

## Bing AI and Image Generation


https://github.com/hibobmaster/matrix_chatgpt_bot/wiki/ <br>
![](https://i.imgur.com/KuYddd5.jpg)
![](https://i.imgur.com/3SRQdN0.jpg)

## Thanks
1. [matrix-nio](https://github.com/poljar/matrix-nio)
2. [acheong08](https://github.com/acheong08)
3. [node-chatgpt-api](https://github.com/waylaidwanderer/node-chatgpt-api)