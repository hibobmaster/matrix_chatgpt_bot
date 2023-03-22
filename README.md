## Introduction
This is a simple Matrix bot that uses OpenAI's GPT API and Bing AI to generate responses to user inputs. The bot responds to four types of prompts: `!gpt`, `!chat` and `!bing` and `!pic` depending on the first word of the prompt.
![demo](https://i.imgur.com/kK4rnPf.jpeg "demo")

## Installation and Setup
Docker method:<br>
Edit `config.json` with proper values <br>
Create an empty file, for persist database only<br>
```bash
touch bot
sudo docker compose up -d
```
<hr>

To run this application, follow the steps below:<br>
1. Clone the repository:
```
git clone https://github.com/hibobmaster/matrix_chatgpt_bot.git
```
2. Install the required dependencies:<br>
```
pip install -r requirements.txt
```
3. Create a new config.json file and fill it with the necessary information:<br>
Use password to login or provide `access_token` <br>
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
- `!gpt` To generate a response using free_endpoint API: 
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
- `!pic` To generate an image from Microsoft Bing
```
!pic A bridal bouquet made of succulents
```
## Bing AI and Image Generation
https://github.com/waylaidwanderer/node-chatgpt-api <br>
https://github.com/hibobmaster/matrix_chatgpt_bot/wiki/Bing-AI <br>
https://github.com/acheong08/EdgeGPT/blob/master/src/ImageGen.py
![](https://i.imgur.com/KuYddd5.jpg)
![](https://i.imgur.com/3SRQdN0.jpg)
