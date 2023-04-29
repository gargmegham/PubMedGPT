# Medical Telegram Bot: Using OpenAI models & SDKs with no daily limits.

We all love [chat.openai.com](https://chat.openai.com), but... It's TERRIBLY laggy, has daily limits, and is only accessible through an archaic web interface.

This repo is ChatGPT re-created as Telegram Bot. **And it works great.**

## Features
- Low latency replies (it usually takes about 3-5 seconds)
- No request limits
- Message streaming
- GPT-4 support
- Support of [ChatGPT API](https://platform.openai.com/docs/guides/chat/introduction)
- List of allowed Telegram users
- Track $ balance spent on OpenAI API
---

## Bot commands
- `/retry` – Regenerate last bot answer
- `/new` – Start new dialog
- `/help` – Show help
- `/register` - Registers patient in MySQL database with details like age, gender, medical history etc. using a ConversationHandler
- `/cancel` - Cancel current conversation
- `/extract` - Extract my prompt data from SQL database
- `/skip` - Skip a registeration step

## Setup
1. Get your [OpenAI API](https://openai.com/api/) key

2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)

3. Edit `config/config.example.yml` to set your tokens and run 2 commands below (*if you're advanced user, you can also edit* `config/config.example.env`):
    ```bash
    mv config/config.example.yml config/config.yml
    mv config/config.example.env config/config.env
    ```

4. 🔥 And now **run**:
    ```bash
    docker-compose --env-file config/config.env up --build
    ```
