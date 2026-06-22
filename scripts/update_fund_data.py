"""基金净值增量更新脚本
每天收盘后运行：只拉每只基金最新一页（30条），新日期追加到 JSON，重新计算信号。
用法: python3 scripts/update_fund_data.py
"""

import json
import re
import urllib.request
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "docs" / "data"
NAV_FILE = DATA_DIR / "fund-nav-6m.json"
CHART_FILE = DATA_DIR / "fund-chart-data.json"

FUNDS = ["014111", "008281", "017811", "025209", "012320", "012733"]


def fetch_latest_page(code: str) -> list[dict]:
    """拉取基金最新一页净值数据（30条）"""
    url = f"https://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz&code={code}&page=1&per=30"
    try:
        resp = urllib.request.urlopen(url, timeout=15).read().decode("utf-8")
        m = re.search(r'content:"(.*?)",records:', resp)
        if not m:
            return []
        content = m.group(1).replace('\\"', '"').replace("\\/", "/")
        cells = re.findall(r"<td[^>]*>([^<]*)</td>", content)
        rows = []
        for chunk in [cells[i : i + 7] for i in range(0, len(cells), 7)]:
            rows.append({
                "date": chunk[0].strip(),
                "nav": float(chunk[1].strip()),
                "change": float(chunk[3].strip().replace("%", "")),
            })
        return rows
    except Exception as e:
        print(f"  [{code}] fetch error: {e}")
        return []


def apply_signals(nav_list: list[dict]) -> list[dict]:
    """对净值序列应用 rules.json 信号检测"""
    signals = []
    for i in range(len(nav_list)):
        today = nav_list[i]
        change = today["change"]
        date = today["date"]

        near_3d_cum = None
        near_2d_cum = None
        near_2d_all_pos = False
        near_2d_all_neg = False
        near_3d_all_neg = False

        if i >= 2:
            cum = 1.0
            for j in range(i - 2, i + 1):
                cum *= 1 + nav_list[j]["change"] / 100
            near_3d_cum = (cum - 1) * 100

        if i >= 1:
            cum2 = (1 + nav_list[i - 1]["change"] / 100) * (1 + change / 100)
            near_2d_cum = (cum2 - 1) * 100
            if nav_list[i - 1]["change"] > 0 and change > 0:
                near_2d_all_pos = True
            if nav_list[i - 1]["change"] < 0 and change < 0:
                near_2d_all_neg = True

        if i >= 2:
            if nav_list[i - 2]["change"] < 0 and nav_list[i - 1]["change"] < 0 and change < 0:
                near_3d_all_neg = True

        matched = None
        # Sell first (sell_overrides_buy)
        if change >= 5:
            matched = ("sell", "single_day_surge_sell", "单日暴涨≥5%")
        elif near_3d_cum is not None and near_3d_cum > 5:
            matched = ("sell", "surge_sell_window", f"近3天累计>{near_3d_cum:.1f}%")
        elif near_2d_all_pos and near_2d_cum is not None and near_2d_cum >= 4 and nav_list[i - 1]["change"] >= 2:
            matched = ("sell", "two_day_up_sell", "连涨2天累计≥4%")
        elif near_3d_all_neg and change < 0:
            matched = ("sell", "three_day_drop_sell", "连跌3天")
        # Buy signals
        elif change <= -5:
            matched = ("buy", "big_drop_buy_heavy", "单日暴跌≥5%")
        elif -5 < change <= -3:
            matched = ("buy", "big_drop_buy", "单日跌3%-5%")
        elif near_3d_cum is not None and near_3d_cum <= -5:
            matched = ("buy", "panic_buy_window", f"连续大跌>{abs(near_3d_cum):.1f}%")
        elif -3 < change <= -2 and near_2d_all_neg:
            matched = ("buy", "moderate_drop_buy", "连续小跌")

        if matched:
            signals.append({
                "date": date, "type": matched[0],
                "rule": matched[1], "desc": matched[2],
                "nav": today["nav"],
            })
    return signals


def build_chart_data(all_data: dict) -> dict:
    """从原始净值数据生成图表数据（周/月聚合 + 信号）"""
    chart_data = {}
    for code, info in all_data.items():
        data = info["data"]
        signals = apply_signals(data)

        weeks, months = {}, {}
        for d in data:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            wk = dt.strftime("%Y-W%W")
            mo = dt.strftime("%Y-%m")
            if wk not in weeks:
                weeks[wk] = {"open": d["nav"], "close": d["nav"], "start": d["date"], "end": d["date"]}
            else:
                weeks[wk]["close"] = d["nav"]
                weeks[wk]["end"] = d["date"]
            if mo not in months:
                months[mo] = {"open": d["nav"], "close": d["nav"], "start": d["date"], "end": d["date"]}
            else:
                months[mo]["close"] = d["nav"]
                months[mo]["end"] = d["date"]

        weekly = []
        for wk in sorted(weeks.keys()):
            w = weeks[wk]
            r = round((w["close"] / w["open"] - 1) * 100, 2)
            weekly.append({"label": w["end"][5:], "date": w["end"], "nav": round(w["close"], 4), "return": r})

        monthly = []
        for mo in sorted(months.keys()):
            m = months[mo]
            r = round((m["close"] / m["open"] - 1) * 100, 2)
            monthly.append({"label": mo, "date": m["end"], "nav": round(m["close"], 4), "return": r})

        chart_data[code] = {
            "name": info["name"],
            "daily": [{"date": d["date"], "nav": d["nav"], "change": d["change"]} for d in data],
            "weekly": weekly,
            "monthly": monthly,
            "signals": signals,
        }
    return chart_data


def update():
    print(f"[{datetime.now():%H:%M:%S}] Updating fund NAV data...")

    if NAV_FILE.exists():
        all_data = json.loads(NAV_FILE.read_text(encoding="utf-8"))
    else:
        all_data = {}

    total_new = 0
    for code in FUNDS:
        # Ensure fund entry exists
        if code not in all_data:
            all_data[code] = {"name": "", "data": []}

        existing_dates = {r["date"] for r in all_data[code]["data"]}
        latest = fetch_latest_page(code)
        time.sleep(0.3)

        new_count = 0
        for row in latest:
            if row["date"] not in existing_dates:
                all_data[code]["data"].append(row)
                existing_dates.add(row["date"])
                new_count += 1

        all_data[code]["data"].sort(key=lambda x: x["date"])
        if new_count > 0:
            total_new += new_count
            print(f"  {code}: +{new_count} new records")
        else:
            print(f"  {code}: up to date")

    if total_new > 0:
        NAV_FILE.write_text(json.dumps(all_data, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved: {total_new} new records total")

        # Regenerate chart data
        chart_data = build_chart_data(all_data)
        CHART_FILE.write_text(json.dumps(chart_data, ensure_ascii=False), encoding="utf-8")
        print(f"  Chart data regenerated")
    else:
        print("  No new data, nothing to update")

    # Print latest record per fund
    print("\n  Latest NAV:")
    for code in FUNDS:
        d = all_data[code]["data"]
        if d:
            latest = d[-1]
            chg = f"{latest['change']:+.2f}%"
            print(f"    {code} {latest['date']}  {latest['nav']:.4f}  {chg}")


if __name__ == "__main__":
    update()
