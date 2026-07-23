import aiohttp
from datetime import date
from config import GIGAPUB_TOKEN, PARTNER_ID, PROJECT_ID

BASE_URL = "https://stat-api.gigapub.tech/v1/statistic"


async def get_stats(start_date: date, end_date: date, group_by: str = "country_code", countries=None):
    """Запрос статистики к GigaPub API.

    group_by: date | country_code | project_id
    """
    headers = {
        "Authorization": f"Bearer {GIGAPUB_TOKEN}",
        "Content-Type": "application/json",
        "x-partner-id": str(PARTNER_ID),
    }

    filters = {"project_id": [PROJECT_ID]}
    if countries:
        filters["countries"] = countries

    payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "group_by": group_by,
        "filters": filters,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", {}).get("rows", [])
