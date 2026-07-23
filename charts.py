import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def geo_cpm_chart(rows: list) -> io.BytesIO:
    """Столбчатый график CPM по гео за текущий день."""
    rows = sorted(rows, key=lambda r: r.get("cpm", 0), reverse=True)
    countries = [r.get("countryCode", r.get("country_code", "?")).upper() for r in rows]
    cpm = [r.get("cpm", 0) for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(countries, cpm, color="#4C8BF5")
    ax.set_title("CPM по гео за сегодня")
    ax.set_ylabel("CPM, $")
    ax.bar_label(bars, fmt="%.2f")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    buf.name = "geo_cpm.png"
    return buf


def weekly_trend_chart(rows: list) -> io.BytesIO:
    """Линейный график дохода/CPM по дням за неделю."""
    rows = sorted(rows, key=lambda r: r.get("date") or r.get("day") or "")
    dates = [r.get("date") or r.get("day") or "?" for r in rows]
    income = [r.get("income", 0) for r in rows]
    cpm = [r.get("cpm", 0) for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(dates, income, marker="o", color="#34A853", label="Доход, $")
    ax1.set_ylabel("Доход, $", color="#34A853")
    ax1.tick_params(axis="x", rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(dates, cpm, marker="s", color="#EA4335", label="CPM, $")
    ax2.set_ylabel("CPM, $", color="#EA4335")

    fig.suptitle("Статистика за неделю")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    buf.name = "weekly_trend.png"
    return buf
