import os
import re
import time
import logging
from groq import Groq

MODEL = "qwen/qwen3-32b"
SYSTEM_PROMPT_RU = "Ты полезный ассистент. Отвечай коротко и по делу."
SYSTEM_PROMPT_EN = "You are a helpful assistant. Keep it short and practical."

_client = None
log = logging.getLogger("ai")

_think_re = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


def _strip_think(s: str) -> str:
    if not s:
        return ""
    s = _think_re.sub("", s)
    return s.strip()


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


def reply(messages: list[dict], max_tokens: int = 1024) -> str:
    t0 = time.perf_counter()
    completion = _get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.6,
        top_p=0.95,
        max_completion_tokens=max_tokens,
    )
    out = _strip_think((completion.choices[0].message.content or "").strip())
    log.info("reply done ms=%d", int((time.perf_counter() - t0) * 1000))
    return out


def chat(user_message: str) -> str:
    return reply(
        [
            {"role": "system", "content": SYSTEM_PROMPT_RU},
            {"role": "user", "content": user_message},
        ]
    )


def analyze_document(content: str, lang: str = "ru") -> str:
    t0 = time.perf_counter()
    sys = SYSTEM_PROMPT_RU if lang == "ru" else SYSTEM_PROMPT_EN
    prompt = (
        f"Analyze this document and give a structured summary:\n\n{content[:12000]}"
        if lang != "ru"
        else f"Сделай структурную выжимку из документа:\n\n{content[:12000]}"
    )
    out = reply(
        [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]
    )
    log.info("analyze done ms=%d chars=%d", int((time.perf_counter() - t0) * 1000), len(content))
    return out
