import aiohttp
from config import GEMINI_API_KEY, GEMINI_MODEL

API_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """Ты — аналитик по монетизации рекламы в Telegram Mini App.
Тебе передают историю статистики (по дням: показы, клики, доход, CPM, CTR)
из рекламной сети GigaPub. Пользователь — разработчик, который управляет
несколькими Telegram-ботами и монетизирует mini app через ad-сети
(GigaPub, Monetag, Taddy, AdGram).

Отвечай кратко, по делу, на русском языке. Давай конкретные, применимые
рекомендации (что изменить в настройках ad-сети, где искать проблему,
на что обратить внимание), а не общие фразы. Если в истории видны аномалии
(резкие скачки CTR, падения CPM, дни без данных) — обязательно отметь их
и предположи возможную причину."""


def _format_history(history_rows: list) -> str:
    if not history_rows:
        return "История пуста — данных пока не накопилось."

    lines = ["date | impressions | clicks | income($) | cpm($) | ctr(%)"]
    for r in history_rows:
        lines.append(
            f"{r['date']} | {r['impressions']} | {r['clicks']} | "
            f"{r['income']:.2f} | {r['cpm']:.2f} | {r['ctr']:.2f}"
        )
    return "\n".join(lines)


async def ask_ai(question: str, history_rows: list) -> str:
    if not GEMINI_API_KEY:
        return (
            "⚠️ GEMINI_API_KEY не задан в .env — AI-советник недоступен.\n"
            "Бесплатный ключ можно получить на aistudio.google.com/apikey"
        )

    history_text = _format_history(history_rows)

    user_content = (
        f"История статистики за последние {len(history_rows)} дн.:\n\n"
        f"{history_text}\n\n"
        f"Вопрос: {question}"
    )

    url = API_URL_TMPL.format(model=GEMINI_MODEL)
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
    }

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                err = data.get("error", {}).get("message", str(data))
                return f"⚠️ Ошибка Gemini API: {err}"

            try:
                candidates = data.get("candidates", [])
                parts = candidates[0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts)
                return text or "⚠️ AI не вернул ответ."
            except (KeyError, IndexError):
                return "⚠️ Не удалось разобрать ответ Gemini API."
