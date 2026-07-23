"""
Тест логики бота без реальных обращений к GigaPub и Telegram API.
Запуск: python test_bot.py
"""
import asyncio
import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "123456:TEST")
os.environ.setdefault("CHAT_ID", "-1000000000000")
os.environ.setdefault("GIGAPUB_TOKEN", "test_token")
os.environ.setdefault("PARTNER_ID", "100")
os.environ.setdefault("PROJECT_ID", "123")

TODAY_GEO_ROWS = [
    {"countryCode": "ru", "impressions": 10000, "clicks": 900, "income": 45.0, "cpm": 4.5},
    {"countryCode": "us", "impressions": 3000, "clicks": 60, "income": 60.0, "cpm": 20.0},
    {"countryCode": "de", "impressions": 1200, "clicks": 20, "income": 18.0, "cpm": 15.0},
]

TODAY_PROJECT_ROWS = [{"impressions": 14200, "clicks": 980, "income": 123.0}]
YESTERDAY_PROJECT_ROWS = [{"impressions": 14000, "clicks": 300, "income": 180.0}]

WEEKLY_ROWS = [
    {"date": "2026-07-17", "impressions": 12000, "clicks": 400, "income": 150.0, "cpm": 12.5},
    {"date": "2026-07-18", "impressions": 13000, "clicks": 420, "income": 160.0, "cpm": 12.3},
    {"date": "2026-07-19", "impressions": 11000, "clicks": 390, "income": 140.0, "cpm": 12.7},
    {"date": "2026-07-20", "impressions": 14500, "clicks": 450, "income": 170.0, "cpm": 11.7},
    {"date": "2026-07-21", "impressions": 15000, "clicks": 470, "income": 180.0, "cpm": 12.0},
    {"date": "2026-07-22", "impressions": 14200, "clicks": 460, "income": 175.0, "cpm": 12.3},
]


async def fake_get_stats(start_date, end_date, group_by="country_code", countries=None):
    if group_by == "country_code":
        return TODAY_GEO_ROWS
    if group_by == "date":
        return WEEKLY_ROWS
    if group_by == "project_id":
        # имитируем разные ответы для сегодня/вчера по датам
        from datetime import date
        if start_date == date.today():
            return TODAY_PROJECT_ROWS
        return YESTERDAY_PROJECT_ROWS
    return []


async def run_tests():
    print("== 1. Проверка форматирования отчётов и графиков ==")
    import main as bot_main

    # form_geo_report / weekly report - без сети
    print(bot_main.format_geo_report(TODAY_GEO_ROWS))
    print()
    print(bot_main.format_weekly_report(WEEKLY_ROWS))
    print()

    chart1 = __import__("charts").geo_cpm_chart(TODAY_GEO_ROWS)
    chart2 = __import__("charts").weekly_trend_chart(WEEKLY_ROWS)
    print(f"geo_cpm_chart: сгенерирован PNG, {len(chart1.getvalue())} байт")
    print(f"weekly_trend_chart: сгенерирован PNG, {len(chart2.getvalue())} байт")

    print("\n== 2. Проверка totals()/детектора аномалий (мок API + мок Telegram) ==")
    with patch("main.get_stats", side_effect=fake_get_stats), \
         patch.object(bot_main.bot, "send_message", new=AsyncMock()) as mock_send_msg, \
         patch.object(bot_main.bot, "send_photo", new=AsyncMock()) as mock_send_photo:

        await bot_main.send_hourly_stats()
        assert mock_send_photo.await_count == 1, "send_photo должен быть вызван 1 раз"
        print("send_hourly_stats: send_photo вызван ✅")

        # теперь полный текстовый отчёт шлётся отдельным send_message (caption только заголовок),
        # плюс алерт аномалии -> итого 2 вызова send_message
        assert mock_send_msg.await_count == 2, "ожидались текст отчёта + алерт аномалии"
        report_text = mock_send_msg.call_args_list[0][0][1]
        assert "Статистика за сегодня" in report_text
        alert_text = mock_send_msg.call_args_list[1][0][1]
        assert "аномал" in alert_text.lower()
        print("check_cpm_anomaly: алерт сработал корректно ✅")
        print("send_hourly_stats: полный отчёт отправлен отдельным сообщением (caption короткий) ✅")

    with patch("main.get_stats", side_effect=fake_get_stats), \
         patch.object(bot_main.bot, "send_message", new=AsyncMock()), \
         patch.object(bot_main.bot, "send_photo", new=AsyncMock()) as mock_send_photo2:
        await bot_main.send_weekly_stats()
        assert mock_send_photo2.await_count == 1
        print("send_weekly_stats: send_photo вызван ✅")

    print("\n== 3. Проверка сохранения истории в storage ==")
    import storage
    history = await storage.get_history(days=30)
    assert len(history) >= 1, "после hourly/weekly отчётов история должна быть не пустой"
    print(f"В истории {len(history)} дней ✅")

    print("\n== 4. Проверка /ask (мок Gemini API, без реального ключа) ==")
    fake_ai_response = {
        "candidates": [
            {"content": {"parts": [{"text": "Тестовая рекомендация: снизь CPM-порог в GigaPub на 10%."}]}}
        ]
    }

    class FakeResp:
        status = 200

        async def json(self):
            return fake_ai_response

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FakeSession:
        def post(self, *a, **kw):
            return FakeResp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    with patch("ai_advisor.aiohttp.ClientSession", return_value=FakeSession()), \
         patch("ai_advisor.GEMINI_API_KEY", "fake-key"):
        import ai_advisor
        answer = await ai_advisor.ask_ai("что улучшить?", history)
        assert "рекомендация" in answer.lower()
        print("ask_ai: получен корректный ответ ✅ ->", answer)

    print("\nВСЕ ПРОВЕРКИ ПРОШЛИ ✅")


if __name__ == "__main__":
    asyncio.run(run_tests())
