import asyncio
import logging
from datetime import date, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, CHAT_ID, CPM_ALERT_THRESHOLD, CTR_ALERT_THRESHOLD
from gigapub import get_stats
from charts import geo_cpm_chart, weekly_trend_chart
import storage
from ai_advisor import ask_ai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def format_geo_report(rows: list) -> str:
    if not rows:
        return "📊 Статистика за сегодня\n\nДанных пока нет."

    total_impr = sum(r.get("impressions", 0) for r in rows)
    total_clicks = sum(r.get("clicks", 0) for r in rows)
    total_income = sum(r.get("income", 0) for r in rows)
    avg_cpm = (total_income / total_impr * 1000) if total_impr else 0

    visible_rows = [
        r for r in rows
        if r.get("impressions", 0) or r.get("clicks", 0) or r.get("income", 0)
    ]

    lines = [f"📊 <b>Статистика за сегодня ({date.today().isoformat()})</b>", ""]
    for r in sorted(visible_rows, key=lambda x: x.get("income", 0), reverse=True):
        code = r.get("countryCode", r.get("country_code", "?")).upper()
        lines.append(
            f"🌍 {code}: показы {r.get('impressions', 0)}, клики {r.get('clicks', 0)}, "
            f"доход ${r.get('income', 0):.2f}, CPM ${r.get('cpm', 0):.2f}"
        )

    lines += [
        "",
        f"<b>Итого:</b> показы {total_impr}, клики {total_clicks}, "
        f"доход ${total_income:.2f}, средний CPM ${avg_cpm:.2f}",
    ]
    return "\n".join(lines)


def format_weekly_report(rows: list) -> str:
    if not rows:
        return "📅 Статистика за неделю\n\nДанных пока нет."

    total_impr = sum(r.get("impressions", 0) for r in rows)
    total_clicks = sum(r.get("clicks", 0) for r in rows)
    total_income = sum(r.get("income", 0) for r in rows)
    avg_cpm = (total_income / total_impr * 1000) if total_impr else 0
    avg_ctr = (total_clicks / total_impr * 100) if total_impr else 0

    lines = ["📅 <b>Статистика за неделю</b>", ""]
    for r in sorted(rows, key=lambda x: x.get("date", "")):
        lines.append(
            f"🗓 {r.get('date')}: показы {r.get('impressions', 0)}, клики {r.get('clicks', 0)}, "
            f"доход ${r.get('income', 0):.2f}, CPM ${r.get('cpm', 0):.2f}"
        )

    lines += [
        "",
        f"<b>Итого за неделю:</b> показы {total_impr}, клики {total_clicks}, "
        f"доход ${total_income:.2f}, средний CPM ${avg_cpm:.2f}, CTR {avg_ctr:.2f}%",
    ]
    return "\n".join(lines)


def totals(rows: list) -> dict:
    impr = sum(r.get("impressions", 0) for r in rows)
    clicks = sum(r.get("clicks", 0) for r in rows)
    income = sum(r.get("income", 0) for r in rows)
    return {
        "impressions": impr,
        "clicks": clicks,
        "income": income,
        "cpm": (income / impr * 1000) if impr else 0,
        "ctr": (clicks / impr * 100) if impr else 0,
    }


async def check_cpm_anomaly():
    """Сравнивает сегодняшние CTR/CPM со вчерашними и шлёт предупреждение при просадке.

    Триггер: CTR вырос сильнее чем на CTR_ALERT_THRESHOLD %, а CPM просел сильнее
    чем на CPM_ALERT_THRESHOLD % — типичный паттерн деградации CPM из-за аномального CTR.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    try:
        today_rows = await get_stats(today, today, group_by="project_id")
        yesterday_rows = await get_stats(yesterday, yesterday, group_by="project_id")
    except Exception:
        logging.exception("Ошибка проверки аномалий CPM/CTR")
        return

    if not today_rows or not yesterday_rows:
        return

    t = totals(today_rows)
    y = totals(yesterday_rows)

    if y["cpm"] == 0 or y["ctr"] == 0:
        return

    cpm_drop_pct = (y["cpm"] - t["cpm"]) / y["cpm"] * 100
    ctr_growth_pct = (t["ctr"] - y["ctr"]) / y["ctr"] * 100

    if cpm_drop_pct >= CPM_ALERT_THRESHOLD and ctr_growth_pct >= CTR_ALERT_THRESHOLD:
        text = (
            "🚨 <b>Похоже на CTR/CPM аномалию</b>\n\n"
            f"CTR сегодня {t['ctr']:.2f}% против {y['ctr']:.2f}% вчера "
            f"(+{ctr_growth_pct:.1f}%)\n"
            f"CPM сегодня ${t['cpm']:.2f} против ${y['cpm']:.2f} вчера "
            f"(−{cpm_drop_pct:.1f}%)\n\n"
            "Стоит проверить источники трафика — рост CTR при просадке CPM обычно "
            "говорит о накрутке кликов или фрод-трафике."
        )
        await bot.send_message(CHAT_ID, text, parse_mode="HTML")


TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4096


async def send_photo_and_report(photo_bytes, filename: str, title: str, full_text: str):
    """Шлёт фото с коротким заголовком в caption, а полный отчёт — отдельным
    сообщением (или несколькими, если превышает лимит Telegram на 4096 символов).
    Так мы не упираемся в лимит caption (1024 символа), сколько бы гео/дней ни было.
    """
    photo = BufferedInputFile(photo_bytes, filename=filename)
    await bot.send_photo(CHAT_ID, photo=photo, caption=title, parse_mode="HTML")

    for i in range(0, len(full_text), TELEGRAM_MESSAGE_LIMIT):
        await bot.send_message(CHAT_ID, full_text[i:i + TELEGRAM_MESSAGE_LIMIT], parse_mode="HTML")


async def send_hourly_stats():
    today = date.today()
    try:
        rows = await get_stats(today, today, group_by="country_code")
    except Exception as e:
        logging.exception("Ошибка получения почасовой статистики")
        await bot.send_message(CHAT_ID, f"⚠️ Не удалось получить статистику: {e}")
        return

    text = format_geo_report(rows)

    if rows:
        visible_rows = [
            r for r in rows
            if r.get("impressions", 0) or r.get("clicks", 0) or r.get("income", 0)
        ]
        chart = geo_cpm_chart(visible_rows or rows)
        await send_photo_and_report(
            chart.read(), "geo_cpm.png", "📊 Статистика за сегодня", text
        )
        await storage.save_daily_stats(today, totals(rows))
    else:
        await bot.send_message(CHAT_ID, text, parse_mode="HTML")

    await check_cpm_anomaly()


async def send_weekly_stats():
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=6)
    try:
        rows = await get_stats(start, end, group_by="date")
    except Exception as e:
        logging.exception("Ошибка получения недельной статистики")
        await bot.send_message(CHAT_ID, f"⚠️ Не удалось получить недельную статистику: {e}")
        return

    text = format_weekly_report(rows)

    if rows:
        chart = weekly_trend_chart(rows)
        await send_photo_and_report(
            chart.read(), "weekly_trend.png", "📅 Статистика за неделю", text
        )
        for r in rows:
            day_totals = {
                "impressions": r.get("impressions", 0),
                "clicks": r.get("clicks", 0),
                "income": r.get("income", 0),
                "cpm": r.get("cpm", 0),
                "ctr": (r.get("clicks", 0) / r["impressions"] * 100) if r.get("impressions") else 0,
            }
            await storage.save_daily_stats(date.fromisoformat(r["date"]), day_totals)
    else:
        await bot.send_message(CHAT_ID, text, parse_mode="HTML")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Бот статистики GigaPub запущен.\n\n"
        "Что делает автоматически:\n"
        "• Каждый час — статистика по гео за сегодня + график CPM\n"
        "• В 00:00 — сводка за неделю + график тренда\n"
        "• Алерт, если CTR резко растёт, а CPM резко падает\n\n"
        "Команды:\n"
        "/stats — статистика за сегодня прямо сейчас\n"
        "/weekly — статистика за неделю прямо сейчас\n"
        "/ask <вопрос> — спросить AI-советника, который видит всю накопленную "
        "историю статистики (например: /ask почему упал CPM в US?)"
    )


@dp.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject):
    question = command.args
    if not question:
        await message.answer(
            "Напиши вопрос после команды, например:\n"
            "<code>/ask Что можно улучшить в монетизации за последнюю неделю?</code>",
            parse_mode="HTML",
        )
        return

    await message.answer("🤔 Анализирую историю статистики...")
    history_rows = await storage.get_history(days=90)
    answer = await ask_ai(question, history_rows)

    for i in range(0, len(answer), 4000):
        await message.answer(answer[i:i + 4000])


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    await message.answer("⏳ Собираю статистику за сегодня...")
    await send_hourly_stats()


@dp.message(Command("weekly"))
async def cmd_weekly(message: Message):
    await message.answer("⏳ Собираю статистику за неделю...")
    await send_weekly_stats()


async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_hourly_stats, "cron", minute=0)
    scheduler.add_job(send_weekly_stats, "cron", hour=0, minute=0)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
