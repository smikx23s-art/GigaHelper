# GigaHelper

Telegram-бот для мониторинга статистики GigaPub с AI-советником на Gemini.

## Возможности

- Каждый час — статистика по гео (показы, клики, доход, CPM) + график CPM по странам + сравнение с вчерашним днём
- В 00:00 — сводка за неделю + график тренда доход/CPM + сравнение с прошлой неделей
- В 09:00 (настраивается) — короткий AI-обзор последних дней без запроса
- Алерт при аномалии CTR/CPM (резкий рост CTR при просадке CPM — типичный признак фрод-трафика)
- Страны с полностью нулевыми показателями скрываются из отчёта и графика
- История всей статистики сохраняется в SQLite
- `/ask <вопрос>` — AI-советник (Google Gemini) видит всю накопленную историю и даёт рекомендации

## Команды бота

- `/start` — справка
- `/stats` — статистика за сегодня прямо сейчас
- `/weekly` — статистика за неделю прямо сейчас
- `/ask <вопрос>` — спросить AI-советника

## Установка

```bash
git clone https://github.com/smikx23s-art/GigaHelper.git
cd GigaHelper
pip install -r requirements.txt
cp .env.example .env
# заполнить .env: BOT_TOKEN, CHAT_ID, GIGAPUB_TOKEN, PROJECT_ID, GEMINI_API_KEY
python main.py
```

Бесплатный ключ Gemini: https://aistudio.google.com/apikey

## Тесты

Проверка логики без реальных обращений к внешним API (моки GigaPub/Telegram/Gemini):

```bash
python test_bot.py
```
