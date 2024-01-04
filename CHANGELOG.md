# Changelog

## 1.5.2
- Expose more stable diffusion webui api parameters

## 1.5.1
- fix: set timeout not work in image generation

## 1.5.0
- Fix localai v2.0+ image generation
- Fallback to gpt-3.5-turbo when caculate tokens using custom model

## 1.4.1
- Fix variable type imported from environment variable
- Bump pre-commit hook version

## 1.4.0
- Fix access_token login method not work in E2EE Room

## 1.3.0
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
