import asyncio
import logging
import os
import tempfile
import time
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

import ai
import db
import extract

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()

TXT = {
    "ru": {
        "hi": "Привет. Это чат-ассистент + разбор PDF/Excel.",
        "pick_lang": "Выбери язык интерфейса:",
        "menu": "Меню",
        "history": "История",
        "reading": "Читаю файл...",
        "no_history": "Истории пока нет.",
        "bad_file": "Пришли PDF или Excel (.xlsx).",
        "extract_fail": "Не смог прочитать файл.",
        "ai_fail": "AI упал, попробуй ещё раз.",
        "lang_set": "Ок, язык сохранён.",
        "ctx_cleared": "Контекст чата очищен.",
        "file_need_task": "Ок, файл принял. Напиши, что с ним сделать (например: «сделай выжимку», «найди риски», «сравни с прошлым месяцем»).",
        "file_dropped": "Ок, файл убрал.",
        "help": "Как пользоваться:\n- просто пиши сообщения\n- или прикрепи PDF/Excel, потом опиши задачу",
    },
    "en": {
        "hi": "Hey. This is a chat assistant + PDF/Excel analysis.",
        "pick_lang": "Pick UI language:",
        "menu": "Menu",
        "history": "History",
        "reading": "Reading file...",
        "no_history": "No history yet.",
        "bad_file": "Send a PDF or Excel (.xlsx).",
        "extract_fail": "Couldn't read the file.",
        "ai_fail": "AI failed, try again.",
        "lang_set": "Ok, saved.",
        "ctx_cleared": "Chat context cleared.",
        "file_need_task": "Got the file. Now tell me what to do with it (ex: summary, risks, action items, compare).",
        "file_dropped": "Ok, dropped the file.",
        "help": "How to use:\n- just send messages\n- or attach a PDF/Excel, then describe the task",
    },
}


def t(lang: str, key: str) -> str:
    if lang not in TXT:
        lang = "ru"
    return TXT[lang].get(key, key)


def kb_lang() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="English", callback_data="lang:en"),
            ]
        ]
    )


def kb_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("🧹 Clear context" if lang == "en" else "🧹 Очистить контекст"),
                    callback_data="action:clear_ctx",
                ),
                InlineKeyboardButton(
                    text=("🗑 Drop file" if lang == "en" else "🗑 Убрать файл"),
                    callback_data="action:drop_file",
                ),
            ],
            [
                InlineKeyboardButton(text=t(lang, "history"), callback_data="action:history"),
                InlineKeyboardButton(
                    text="🌐 " + ("Language" if lang == "en" else "Язык"),
                    callback_data="action:lang",
                ),
            ],
        ]
    )

async def show_menu(message: Message, lang: str):
    await message.answer(
        f"{t(lang, 'hi')}\n\n<b>{t(lang, 'menu')}</b>",
        reply_markup=kb_menu(lang),
        parse_mode="HTML",
    )
    await message.answer(t(lang, "help"))


@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    lang = db.get_lang(uid)
    log.info("start user=%s lang=%s", uid, lang)
    await message.answer(t(lang, "pick_lang"), reply_markup=kb_lang())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    uid = message.from_user.id
    lang = db.get_lang(uid)
    await message.answer(t(lang, "help"), reply_markup=kb_menu(lang))


@dp.message(Command("history"))
async def cmd_history(message: Message):
    uid = message.from_user.id
    lang = db.get_lang(uid)
    rows = db.get_history(uid)
    if not rows:
        await message.answer(t(lang, "no_history"), reply_markup=kb_menu(lang))
        return
    lines = []
    for ts, filename, summary in rows:
        lines.append(f"<b>{ts}</b> | {filename}\n{summary}")
    await message.answer("\n\n".join(lines), parse_mode="HTML", reply_markup=kb_menu(lang))


@dp.callback_query()
async def on_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    data = cb.data or ""
    lang = db.get_lang(uid)
    log.info("cb user=%s data=%s", uid, data)

    if data.startswith("lang:"):
        new_lang = data.split(":", 1)[1]
        db.set_lang(uid, new_lang)
        lang = db.get_lang(uid)
        await cb.message.answer(t(lang, "lang_set"))
        await show_menu(cb.message, lang)
        await cb.answer()
        return

    if data == "action:lang":
        await cb.message.answer(t(lang, "pick_lang"), reply_markup=kb_lang())
        await cb.answer()
        return

    if data == "action:history":
        rows = db.get_history(uid)
        if not rows:
            await cb.message.answer(t(lang, "no_history"), reply_markup=kb_menu(lang))
        else:
            lines = [f"<b>{ts}</b> | {filename}\n{summary}" for ts, filename, summary in rows]
            await cb.message.answer("\n\n".join(lines), parse_mode="HTML", reply_markup=kb_menu(lang))
        await cb.answer()
        return

    if data == "action:clear_ctx":
        db.clear_msgs(uid)
        await cb.message.answer(t(lang, "ctx_cleared"), reply_markup=kb_menu(lang))
        await cb.answer()
        return

    if data == "action:drop_file":
        db.clear_pending_file(uid)
        await cb.message.answer(t(lang, "file_dropped"), reply_markup=kb_menu(lang))
        await cb.answer()
        return

    await cb.answer()


@dp.message(F.document)
async def handle_document(message: Message):
    uid = message.from_user.id
    lang = db.get_lang(uid)
    doc: Document = message.document
    filename = doc.file_name or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext not in ("pdf", "xlsx", "xls"):
        await message.answer(t(lang, "bad_file"), reply_markup=kb_menu(lang))
        return

    log.info("doc user=%s file=%s", uid, filename)
    await message.answer(t(lang, "reading"))

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await bot.download(doc, destination=tmp_path)

        if ext == "pdf":
            text = extract.extract_pdf(tmp_path)
        else:
            text = extract.extract_excel(tmp_path)

        if not text:
            await message.answer(t(lang, "extract_fail"), reply_markup=kb_menu(lang))
            return

    except Exception as e:
        log.exception("extract fail user=%s err=%s", uid, e)
        await message.answer(t(lang, "extract_fail"), reply_markup=kb_menu(lang))
        return
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    db.set_pending_file(uid, filename, text[:20000], ts)
    await message.answer(t(lang, "file_need_task"), reply_markup=kb_menu(lang))


@dp.message(F.text)
async def handle_text(message: Message):
    uid = message.from_user.id
    lang = db.get_lang(uid)
    user_text = (message.text or "").strip()
    if not user_text:
        return

    pending = db.get_pending_file(uid)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if pending:
        fname, ftxt = pending
        user_text = (
            f"Задача: {user_text}\n\nФайл: {fname}\n\nСодержимое:\n{ftxt}"
            if lang == "ru"
            else f"Task: {user_text}\n\nFile: {fname}\n\nContent:\n{ftxt}"
        )
        db.clear_pending_file(uid)

    db.add_msg(uid, "user", user_text, ts)

    sys = "Ты полезный ассистент. Учитывай историю диалога. Отвечай по делу." if lang == "ru" else "You are a helpful assistant. Use chat history. Be practical."
    msgs = [{"role": "system", "content": sys}]
    for role, content in db.get_msgs(uid, limit=16):
        if role in ("user", "assistant"):
            msgs.append({"role": role, "content": content})

    t0 = time.perf_counter()
    try:
        reply = ai.reply(msgs, max_tokens=1024)
    except Exception as e:
        log.exception("ai chat fail user=%s err=%s", uid, e)
        await message.answer(t(lang, "ai_fail"), reply_markup=kb_menu(lang))
        return

    log.info("chat ok user=%s ms=%d", uid, int((time.perf_counter() - t0) * 1000))
    db.add_msg(uid, "assistant", reply, ts)

    if pending:
        db.insert_log(ts, uid, pending[0], reply)

    await message.answer(reply, reply_markup=kb_menu(lang))


async def main():
    db.init_db()
    log.info("bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
