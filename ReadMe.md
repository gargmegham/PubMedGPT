# Medical Telegram Bot: Using OpenAI models & SDKs with no daily limits.

We all love [chat.openai.com](https://chat.openai.com), but... It's TERRIBLY laggy, has daily limits, and is only accessible through an archaic web interface.

This repo is MedicalGPT re-created as Telegram Bot. **And it works great.**

## Features
- Low latency replies (it usually takes about 3-5 seconds)
- No request limits
- Message streaming
- Support of [ChatGPT API](https://platform.openai.com/docs/guides/chat/introduction)
- List of allowed Telegram users
- This bot has been created under the guidance of a certified Dr.
- This bot understands when certain sentences indicates certain diseases or concerns, and then it asks follow up questions accordingly.
- It also prescribes users based on thier medical conditions, medications, surgeries, allergies etc. which it asks for during registeration process.
- This also allows you to integrate your cal.com account, which allows you to book appointments for specialized treatment from Dr.
---

## Upcoming Features
* Invoicing
* Payment gateway integratiom
* PDF prescription generation with a sign from certified professional after review of patient case and prescribed medications
---

## Bot commands
- `/retry` – Regenerate last bot answer
- `/new` – Start fresh dialog
- `/help` – Show command options
- `/register` - Register patient in database with details like age, gender, medical history etc.
- `/cancel` - Cancel current conversation
- `/diagnose` - Diagnose for a disease
- `/call` - Book an appointment
- `/choose` - Choose a concern which fits your query

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
    docker-compose --env-file config/config.env up --build -d
    ```
