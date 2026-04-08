# tg-bot-mvp

telegram bot: chat assistant + pdf/xlsx text extraction, answers via [groq](https://groq.com/) (qwen3-32b). sqlite stores language, messages, and short file-analysis history.

**env** (`.env`):

```
TELEGRAM_TOKEN=   # from @BotFather
GROQ_API_KEY=     # groq cloud console
```

**run**

```bash
pip install -r requirements.txt
python bot.py
```

send messages as usual, or attach a `.pdf` / `.xlsx` (`.xls`), then describe what you want (summary, risks, etc.). ru/en ui from `/start`.
