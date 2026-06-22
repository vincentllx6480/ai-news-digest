"""基金每日分析文本自动生成
读取 fund-chart-data.json，基于机械规则更新 fund.html 中的每日分析区块。
用法: python3 scripts/update_fund_analysis.py
"""
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CHART_FILE = BASE_DIR / "docs" / "data" / "fund-chart-data.json"
FUND_HTML = BASE_DIR / "docs" / "fund.html"

FUND_INFO = {
    "014111": "嘉实稀有金属ETF联接C",
    "008281": "国泰CES半导体芯片ETF联接A",
    "017811": "东方人工智能主题混合C",
    "025209": "永赢先锋半导体智选混合发起C",
    "012320": "东财消费电子指数增强C",
    "012733": "易方达中证人工智能主题ETF联接A",
}

FUND_SECTOR = {
    "014111": "稀有金属",
    "008281": "半导体芯片",
    "017811": "人工智能/半导体",
    "025209": "半导体智选",
    "012320": "消费电子",
    "012733": "人工智能",
}

SIGNAL_BADGES = {
    "buy": '<span class="badge badge-buy">买入信号</span>',
    "sell": '<span class="badge badge-sell">卖出信号</span>',
    "hold": '<span class="badge badge-hold">持有</span>',
}


def load_data():
    with open(CHART_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_latest_signals(fund_data):
    """获取最近5天的信号"""
    signals = fund_data.get("signals", [])
    daily = fund_data.get("daily", [])
    if not daily:
        return [], None

    latest_date = daily[-1]["date"]
    recent_signals = [s for s in signals if s["date"] >= latest_date]
    # Get last 2 signals regardless of date
    last_signals = signals[-3:] if len(signals) >= 3 else signals
    return last_signals, daily


def analyze_fund(code, fund_data):
    """对单只基金做机械分析"""
    daily = fund_data.get("daily", [])
    if len(daily) < 3:
        return "hold", "数据不足，无法分析"

    latest = daily[-1]
    prev = daily[-2] if len(daily) >= 2 else None
    prev2 = daily[-3] if len(daily) >= 3 else None

    change = latest["change"]
    nav = latest["nav"]
    date = latest["date"]

    # 计算近2天、近3天累计涨跌
    cum2 = None
    cum3 = None
    if prev:
        cum2 = ((1 + prev["change"] / 100) * (1 + change / 100) - 1) * 100
    if prev2 and prev:
        cum3 = ((1 + prev2["change"] / 100) * (1 + prev["change"] / 100) * (1 + change / 100) - 1) * 100

    signal_type = "hold"
    reasons = []

    # 卖出判断（优先）
    if change >= 5:
        signal_type = "sell"
        reasons.append(f"单日暴涨{change:+.2f}%，触发卖出信号")
    elif cum3 and cum3 > 5:
        signal_type = "sell"
        reasons.append(f"近3天累计涨{cum3:.1f}%，短线获利盘压力大")
    elif cum2 and cum2 >= 4 and prev and prev["change"] >= 2 and change > 0:
        signal_type = "sell"
        reasons.append(f"连涨2天累计{cum2:.1f}%，建议减仓锁定利润")
    elif cum2 and prev and prev["change"] < 0 and change < 0 and prev2 and prev2["change"] < 0:
        signal_type = "sell"
        reasons.append("连跌3天，触发止损信号")

    # 买入判断
    if change <= -5:
        signal_type = "buy"
        reasons.append(f"单日暴跌{change:+.2f}%，触发重仓买入信号")
    elif change <= -3:
        signal_type = "buy"
        reasons.append(f"单日跌{change:+.2f}%，触发买入信号")
    elif cum3 and cum3 <= -5:
        signal_type = "buy"
        reasons.append(f"连续大跌{cum3:.1f}%，触发抄底窗口")
    elif cum2 and prev and change < 0 and prev["change"] < 0 and change > -3:
        signal_type = "buy"
        reasons.append("连续小跌，可分批建仓")

    # 持有分析
    if signal_type == "hold":
        if change > 0:
            reasons.append(f"今日+{change:.2f}%，趋势向好")
        elif change < 0:
            reasons.append(f"今日{change:+.2f}%，短期回调")
        else:
            reasons.append("今日平盘")

    # 附加统计
    if cum2:
        desc = f"近2天累计{cum2:+.1f}%"
    else:
        desc = ""
    if cum3:
        desc += f"，近3天累计{cum3:+.1f}%"

    text = f"{date} NAV {nav:.4f}，{'、'.join(reasons)}。{desc}。"

    return signal_type, text


def generate_analysis_html(data):
    """生成每日分析 HTML 区块"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 收集各基金分析结果
    results = {}
    up_count = 0
    down_count = 0
    sectors_up = {}
    sectors_down = {}

    for code in FUND_INFO:
        if code not in data:
            continue
        fd = data[code]
        daily = fd.get("daily", [])
        if not daily:
            continue

        latest = daily[-1]
        sig, text = analyze_fund(code, fd)
        results[code] = {"signal": sig, "text": text, "change": latest["change"], "date": latest["date"]}

        if latest["change"] > 0:
            up_count += 1
            s = FUND_SECTOR.get(code, "")
            sectors_up[s] = sectors_up.get(s, 0) + latest["change"]
        else:
            down_count += 1
            s = FUND_SECTOR.get(code, "")
            sectors_down[s] = sectors_down.get(s, 0) + abs(latest["change"])

    # 盘面综述
    latest_dates = sorted(set(r["date"] for r in results.values()))
    data_date = latest_dates[-1] if latest_dates else today_str

    best_sector = max(sectors_up, key=sectors_up.get) if sectors_up else "无"
    worst_sector = max(sectors_down, key=sectors_down.get) if sectors_down else "无"

    if up_count >= 4:
        overview = f"{data_date} 5只持仓基金{up_count}涨{down_count}跌，整体偏强。{best_sector}板块表现最亮眼。"
    elif down_count >= 4:
        overview = f"{data_date} 5只持仓基金{up_count}涨{down_count}跌，整体偏弱。{worst_sector}板块回调明显，注意风险控制。"
    else:
        overview = f"{data_date} 5只持仓基金{up_count}涨{down_count}跌，板块分化。{best_sector}走强，{worst_sector}走弱。"

    # 风险提示
    sell_count = sum(1 for r in results.values() if r["signal"] == "sell")
    buy_count = sum(1 for r in results.values() if r["signal"] == "buy")
    risks = []
    if sell_count >= 2:
        risks.append(f"{sell_count}只基金触发卖出信号，短线注意减仓锁定利润")
    if buy_count >= 2:
        risks.append(f"{buy_count}只基金触发买入信号，可关注建仓机会")
    if not risks:
        risks.append("短线无极端信号，维持现有仓位观察")
    risk_text = "；".join(risks) + "。"

    # 生成各基金 HTML
    fund_cards = []
    for code in ["014111", "008281", "017811", "025209", "012320", "012733"]:
        if code not in results:
            continue
        r = results[code]
        badge = SIGNAL_BADGES.get(r["signal"], SIGNAL_BADGES["hold"])
        fund_cards.append(f"""    <div class="fund-note" id="fn-{code}">
      <span class="fn-code">{code}</span><span class="fn-name">{FUND_INFO[code]}</span>
      <div class="fn-signal">{badge}</div>
      <div class="fn-text">{r['text']}</div>
    </div>""")

    fund_cards_html = "\n".join(fund_cards)

    html = f"""<div class="daily-analysis" id="daily-analysis">
  <div class="da-header">
    <h2>今日盘面分析</h2>
    <span class="da-date" id="da-date">{today_str}</span>
    <span class="da-tag overview">盘面综述</span>
  </div>
  <div class="overview-text" id="da-overview">
    {overview}
  </div>

  <h3>各基金信号解读</h3>
  <div class="fund-notes" id="da-fund-notes">
{fund_cards_html}
  </div>

  <div class="risk-note" id="da-risk">
    <strong>风险提示：</strong>{risk_text}
  </div>
</div>
<!-- ═══════════════════════════════════════════ -->
<!-- END DAILY ANALYSIS BLOCK -->
<!-- ═══════════════════════════════════════════ -->"""

    return html


def update_fund_html():
    data = load_data()
    new_analysis = generate_analysis_html(data)
    new_analysis = "\n".join(line for line in new_analysis.split("\n"))

    with open(FUND_HTML, encoding="utf-8") as f:
        html = f.read()

    # 匹配 daily-analysis div 到 END DAILY ANALYSIS BLOCK
    pattern = r'<div class="daily-analysis" id="daily-analysis">.*?<!-- END DAILY ANALYSIS BLOCK -->\s*<!-- ═+ -->'
    if re.search(pattern, html, re.DOTALL):
        new_html = re.sub(pattern, new_analysis, html, count=1, flags=re.DOTALL)
        with open(FUND_HTML, "w", encoding="utf-8") as f:
            f.write(new_html)
        print("  fund.html daily analysis updated")
        return True
    else:
        print("  ERROR: daily-analysis block not found in fund.html")
        return False


if __name__ == "__main__":
    print(f"[{datetime.now():%H:%M:%S}] Updating fund daily analysis...")
    update_fund_html()
