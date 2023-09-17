# Changelog

## 1.3.0(unreleased)
- remove support for bing,bard,pandora
- refactor chat logic, add self host model support
- support new image generation endpoint
- admin system to manage langchain(flowise backend)

## 1.2.0
- rename `api_key` to `openai_api_key` in `config.json`
- rename `bing_api_endpoint` to `api_endpoint` in `config.json` and `env` file
- add `temperature` option to control ChatGPT model temperature
- remove `jailbreakEnabled` option
- session isolation for `!chat`, `!bing`, `!bard` command
- `!new + {chat,bing,bard,talk}` now can be used to create new conversation
- send some error message to user
- bug fix and code cleanup
