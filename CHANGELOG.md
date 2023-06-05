# Changelog

## 1.2.0
- rename `api_key` to `openai_api_key` in `config.json`
- rename `bing_api_endpoint` to `api_endpoint` in `config.json` and `env` file
- add `temperature` option to control ChatGPT model temperature
- remove `jailbreakEnabled` option
- session isolation for `!chat`, `!bing`, `!bard` command
- `!new + {chat,bing,bard,talk}` now can be used to create new conversation
- send some error message to user
- bug fix and code cleanup
