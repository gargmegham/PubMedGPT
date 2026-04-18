<div>
<img src="https://github.com/gargmegham/MedicalGPT/assets/95271253/75be92df-41e5-46b2-908d-4fc55df236ca" width="50" height="50">
<h1>MedicalGPT — AI Medical Assistant Telegram Bot</h1>
</div>

A Telegram bot that provides AI-powered medical consultation using OpenAI's GPT-4. Patients can register their medical history, receive symptom-based follow-up questions, and get filtered medication recommendations — all within Telegram. Built under the guidance of a certified doctor.

---

## Features

- **Conversational AI** — Powered by GPT-4, acting as a personal medical assistant named "Maya"
- **Patient registration** — Collects age, gender, allergies, current medications, surgeries, medical conditions, and pregnancy status
- **Symptom detection** — Automatically detects when a message indicates a medical concern and routes to a structured diagnosis flow
- **Prescription filtering** — Medication recommendations are filtered against each patient's profile (allergies, conditions, medications, demographics)
- **Message streaming** — Real-time response delivery via Telegram with typing indicators
- **Appointment booking** — cal.com integration allows booking with a specialist directly from the bot
- **Access control** — Optionally restrict the bot to a list of allowed Telegram usernames/user IDs
- **Conversation history** — Dialog stored in MySQL with automatic context pruning when token limits are approached; sessions reset after a configurable timeout

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot |
| `/help` | Show available commands |
| `/register` | Register as a patient (collects medical history) |
| `/diagnose` | Start a structured disease diagnosis flow |
| `/choose` | Select a concern that best fits your query |
| `/call` | Book an appointment with a recommended doctor |
| `/new` | Start a fresh conversation |
| `/retry` | Regenerate the last bot response |
| `/cancel` | Cancel the current conversation or task |

---

## Tech Stack

- **Language:** Python 3.8+
- **Telegram:** `python-telegram-bot` 20.x
- **AI:** OpenAI API (`gpt-4`) via `openai` 0.27.x
- **Database:** MySQL via SQLAlchemy ORM
- **Async:** `aiohttp`, `aiolimiter`
- **Config:** YAML + `.env`
- **Deployment:** Docker & Docker Compose
- **External:** AWS Lambda for cal.com webhook handling

---

## Setup

### Prerequisites

- Docker and Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A running MySQL instance

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/gargmegham/MedicalGPT.git
cd MedicalGPT
```

**2. Create configuration files**

```bash
mv config/config.example.yml config/config.yml
mv config/config.example.env config/config.env
```

**3. Edit `config/config.yml`**

```yaml
telegram_token: ""              # From @BotFather
openai_api_key: ""              # From OpenAI
use_chatgpt_api: true
allowed_telegram_usernames: []  # Leave empty for public access, or list usernames/user IDs
new_dialog_timeout: 600         # Seconds of inactivity before a new dialog starts
developer_telegram_chatid: ""   # Your Telegram chat ID — receives error notifications
admin_telegram_username: ""     # Admin username
```

**4. Edit `config/config.env`**

```env
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DATABASE=chatgpt
```

**5. Run with Docker Compose**

```bash
docker-compose --env-file config/config.env up --build -d
```

---

## Running Locally (Development)

```bash
pip install -r requirements.txt
python3 bot/bot.py
```

---

## Project Structure

```
PubMedGPT/
├── bot/
│   ├── bot.py                  # Entry point, bot initialization
│   ├── config.py               # Config loader
│   ├── medicalgpt.py           # GPT interaction and token management
│   ├── mysql.py                # Database operations and prescription logic
│   ├── tables.py               # SQLAlchemy table definitions
│   ├── filters.py              # Custom Telegram message filters
│   ├── utils.py                # Utility helpers
│   └── handlers/
│       ├── commands.py         # Command handlers (/start, /help, etc.)
│       ├── disease.py          # Disease diagnosis conversation flow
│       ├── message.py          # Message streaming handler
│       └── registeration.py   # Patient registration conversation flow
├── config/
│   ├── config.example.yml      # YAML config template
│   ├── config.example.env      # ENV config template
│   └── chat_modes.yml          # System prompts for different chat modes
├── lambda_cal.com/
│   └── lambda_function.py      # AWS Lambda for cal.com booking webhooks
├── training_data/              # Disease-specific JSONL training datasets
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `user` | Patient profiles — demographics, medical history |
| `dialog` | Conversation history stored as JSON |
| `disease` / `disease_question` | Structured diagnosis questions per disease |
| `medicine` | Medication database with eligibility filters |
| `disposition` | Prescriptions issued per patient/disease |
| `booking` | Appointment records from cal.com |

---

## cal.com Integration

The `lambda_cal.com/` directory contains an AWS Lambda function that handles cal.com webhook events (`BOOKING_CREATED`, `BOOKING_CANCELLED`). It records bookings in the database and can notify the patient via Telegram.

Booking link template: `https://cal.com/<your-username>/telegram-medicalgpt`

---

## Upcoming Features

- Invoicing and payment gateway integration
- PDF prescription generation with certified professional sign-off after case review

---

## Disclaimer

This bot is intended as an informational aid and does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider for medical decisions.
