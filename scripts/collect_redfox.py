#!/usr/bin/env python3
"""RedFox Data Collector - 红狐数据 API 采集脚本 (v2)

从红狐数据 API 采集抖音/小红书/公众号/全网热点四平台的 AI 相关热点数据。
使用精准关键词 + 后置相关性过滤，避免蹭标签内容。

API 端点来源: RedFox Community Skills (douyin-search, xiaohongshu-weeklytop, wechat-10w-hot, trending-hub)
认证方式: X-API-KEY 请求头

用法:
    python3 collect_redfox.py --api-key YOUR_KEY [--output data.json] [--start YYYY-MM-DD] [--end YYYY-MM-DD]

    默认采集昨天→今天的最新内容（按发布时间倒序）。
    不传日期参数时，自动使用昨日~今日范围。
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta

REDFOX_BASE = "https://redfox.hk/story/api"

# === 关键词策略 ===
# 使用具体的技术/公司/事件名，避免泛词匹配到蹭标签内容
KEYWORDS_DOUYIN = [
    "DeepSeek",          # 模型发布/技术讨论
    "OpenAI ChatGPT",    # OpenAI 动态
    "Claude Anthropic",  # Claude 相关
    "AI融资",            # AI 融资事件
    "大模型发布",        # 模型发布
]

KEYWORDS_XHS = [
    "DeepSeek",
    "Claude",
    "AI 编程",
    "ChatGPT",
    "大模型",
    "AI 工具",
]

KEYWORDS_WECHAT = [
    "DeepSeek",
    "OpenAI",
    "Claude",
    "AI Agent",
    "大模型发布",
]

KEYWORDS_HOTSPOT = [
    "AI", "人工智能", "大模型", "OpenAI", "DeepSeek",
]


# === 相关性过滤 ===
# 标题包含这些模式的内容大概率是蹭标签/内容农场，直接丢弃
NOISE_PATTERNS = [
    r'#\w+创作浪潮',       # 蹭抖音AI创作标签
    r'#手搓\w+',            # 手工DIY蹭标签
    r'#vlog.*扶持',         # 流量扶持标签
    r'过去五年AI的变化',    # 无信息量对比视频
    r'熊出没',              # 完全无关
    r'早餐奶奶',            # 完全无关
    r'篮球摄手虎',          # 无关
    r'引航员',              # 无关
    r'数字永远无法定义',    # 无关鸡汤
    r'奥迪E7X',             # 汽车广告
    r'这AI视频的尺度',      # 明星+AI蹭热度
    r'这真的不是AI吗',      # 低质标题党
    r'早期人类.*ai',        # 无信息量 meme
    r'喵喵爱吃娱',          # 娱乐账号蹭AI
    r'小明修仙传',          # AI标签的二次元内容
    r'作业帮',              # 用AI标签的教育广告
]

# 标题必须包含至少一个 AI 相关信号词
AI_SIGNALS = [
    "AI", "ai", "人工智能", "大模型", "GPT", "LLM", "Claude", "claude",
    "DeepSeek", "deepseek", "OpenAI", "openai", "ChatGPT", "chatgpt",
    "Agent", "智能体", "机器学习", "深度学习", "神经网络", "NLP",
    "Anthropic", "模型发布", "AI融资", "融资.*AI", "AI.*融资",
    "编程.*AI", "AI.*编程", "Codex", "Gemini", "Llama",
    "机器人", "AI 视频", "AI视频", "AI创作大赛", "AI.*大赛",
]


def is_relevant(title: str) -> bool:
    """检查标题是否真正与 AI 相关（非蹭标签）"""
    if not title or len(title) < 4:
        return False

    # 噪声过滤
    for pat in NOISE_PATTERNS:
        if re.search(pat, title):
            return False

    # AI 信号匹配：
    # - ASCII 短信号（AI, GPT, LLM）：用词边界 \b 防止 "DaiDai" 误匹配
    # - 中文信号 + 长 ASCII 信号：直接子串匹配
    for sig in AI_SIGNALS:
        if sig.isascii() and len(sig) <= 3:
            if re.search(r'(?<![a-zA-Z])' + re.escape(sig) + r'(?![a-zA-Z])', title):
                return True
        else:
            if re.search(sig, title):
                return True

    return False


def call_api(url: str, payload: dict, api_key: str, timeout: int = 15) -> dict:
    """POST 请求"""
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode("utf-8")[:500]}
    except Exception as e:
        return {"error": str(e)}


def dedup_by_title(items: list) -> list:
    """按标题去重"""
    seen = set()
    result = []
    for item in items:
        t = item.get("title", "").strip().lower()
        # Normalize: remove common noise
        t = re.sub(r'\s+', '', t)
        if t and t not in seen:
            seen.add(t)
            result.append(item)
    return result


def collect_douyin(api_key: str, start_date: str = "", end_date: str = "") -> list:
    """抖音: 关键词搜索 → 相关性过滤 → 去重排序（按发布时间倒序）"""
    url = f"{REDFOX_BASE}/dy/search/search"
    results = []

    for kw in KEYWORDS_DOUYIN:
        payload = {"keyword": kw, "source": "AI速递-v3"}
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        resp = call_api(url, payload, api_key)
        if resp.get("code") == 2000:
            articles = resp.get("data", {}).get("articles", [])
            for a in articles:
                title = a.get("title", "")
                if is_relevant(title):
                    results.append({
                        "platform": "douyin",
                        "title": title,
                        "author": a.get("accountName", ""),
                        "likeCount": a.get("likeCount", 0) or 0,
                        "commentCount": a.get("commentCount", 0) or 0,
                        "shareCount": a.get("shareCount", 0) or 0,
                        "collectCount": a.get("collectCount", 0) or 0,
                        "workUrl": a.get("workUrl", ""),
                        "coverUrl": a.get("coverUrl", ""),
                        "publishTime": a.get("publishTime", ""),
                        "keyword": kw,
                    })
        time.sleep(0.3)

    results = dedup_by_title(results)
    # 按发布时间倒序（最新在前）
    results.sort(key=lambda x: x["publishTime"], reverse=True)
    return results[:8]


def collect_xiaohongshu(api_key: str, start_date: str = "", end_date: str = "") -> list:
    """小红书: 关键词搜索 → 相关性过滤 → 去重排序（按发布时间倒序）"""
    url = f"{REDFOX_BASE}/xhs/search/search"
    results = []

    for kw in KEYWORDS_XHS:
        payload = {"keyword": kw, "source": "AI速递-v3"}
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        resp = call_api(url, payload, api_key)
        if resp.get("code") == 2000:
            articles = resp.get("data", {}).get("articles", [])
            for a in articles:
                title = a.get("title", "")
                if not is_relevant(title):
                    continue
                results.append({
                    "platform": "xiaohongshu",
                    "title": title,
                    "author": a.get("authorNickname", ""),
                    "fansCount": int(a.get("authorFans", 0) or 0),
                    "likeCount": int(a.get("likedCount", 0) or 0),
                    "commentCount": int(a.get("commentsCount", 0) or 0),
                    "collectCount": int(a.get("collectedCount", 0) or 0),
                    "shareCount": int(a.get("sharedCount", 0) or 0),
                    "interactiveCount": int(a.get("interactiveCount", 0) or 0),
                    "relevanceScore": float(a.get("relevanceScore", 0) or 0),
                    "workUrl": a.get("shareInfoLink", ""),
                    "coverUrl": a.get("cover", ""),
                    "publishTime": a.get("createTime", ""),
                    "keyword": kw,
                })
        time.sleep(0.3)

    results = dedup_by_title(results)
    # XHS 按互动数排序
    def score(r):
        return (r["likeCount"] or 0) + (r["collectCount"] or 0)*2 + (r["commentCount"] or 0)*3
    results.sort(key=score, reverse=True)
    return results[:8]


def collect_wechat(api_key: str, start_date: str = "", end_date: str = "") -> list:
    """公众号: 关键词搜索 → 相关性过滤 → 取最新文章（API 数据有延迟，不做严格日期过滤）"""
    url = f"{REDFOX_BASE}/gzhData/searchArticle"
    results = []

    for kw in KEYWORDS_WECHAT:
        resp = call_api(url, {
            "keyword": kw,
            "offset": 0,
            "count": 10,
            "sortType": "_4",
        }, api_key)

        if resp.get("code") == 2000:
            for item in resp.get("data", {}).get("list", [])[:3]:
                title = item.get("title", "")
                if not is_relevant(title):
                    continue
                results.append({
                    "platform": "wechat",
                    "title": title,
                    "author": item.get("author", ""),
                    "readCount": item.get("readCount", 0) or 0,
                    "likeCount": item.get("likeCount", 0) or 0,
                    "commentCount": item.get("commentCount", 0) or 0,
                    "shareCount": item.get("shareCount", 0) or 0,
                    "workUrl": item.get("workUrl", ""),
                    "publishTime": item.get("publishTime", ""),
                    "keyword": kw,
                })
        time.sleep(0.2)

    results = dedup_by_title(results)
    results.sort(key=lambda x: x["publishTime"], reverse=True)
    # 过滤超过 14 天的内容
    cutoff = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    results = [r for r in results if r["publishTime"][:10] >= cutoff]
    return results[:8]


def collect_hotspot(api_key: str, start_date: str = "", end_date: str = "") -> list:
    """全网热点: 关键词筛选 → 去重排序（按发布时间倒序）"""
    url = f"{REDFOX_BASE}/hotSpot/getListByPlatformWithKeyword"
    results = []
    payload = {
        "source": "AI速递-v3",
        "platforms": [2, 5, 9, 8],  # dy, wb, zh, bz
        "keywords": KEYWORDS_HOTSPOT,
    }
    if start_date:
        payload["startDate"] = start_date + " 00:00:00"
    if end_date:
        payload["endDate"] = end_date + " 23:59:59"
    resp = call_api(url, payload, api_key)

    if resp.get("code") == 2000:
        data = resp.get("data", {})
        for key in ["dyList", "wbList", "zhList", "bzList"]:
            for item in data.get(key, [])[:3]:
                title = item.get("title", "")
                if is_relevant(title):
                    results.append({
                        "platform": "hotspot",
                        "title": title,
                        "hotCount": item.get("hotCount", 0) or 0,
                        "platName": {"dyList": "抖音", "wbList": "微博", "zhList": "知乎", "bzList": "B站"}.get(key, key),
                        "url": item.get("url", ""),
                        "gmtCreate": item.get("gmtCreate", ""),
                    })

    results = dedup_by_title(results)
    results.sort(key=lambda x: x["gmtCreate"], reverse=True)
    return results[:10]


def collect_all(api_key: str, output_path: str = None,
                start_date: str = "", end_date: str = "") -> dict:
    """采集所有平台数据"""
    if not start_date:
        # 默认：3天前 → 今天（考虑 API 数据延迟 12-24h）
        today = datetime.now()
        start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    print(f"[{datetime.now():%H:%M:%S}] RedFox v3 Collection Started")
    print(f"  日期范围: {start_date} → {end_date}")
    print(f"  策略: 精准关键词 + 相关性过滤 + 按发布时间倒序")

    result = {
        "collectedAt": datetime.now().isoformat(),
        "dateRange": {"start": start_date, "end": end_date},
        "platforms": {},
        "errors": [],
        "totals": {},
    }

    for name, collector in [
        ("douyin", collect_douyin),
        ("xiaohongshu", collect_xiaohongshu),
        ("wechat", collect_wechat),
        ("hotspot", collect_hotspot),
    ]:
        label = {"douyin": "抖音", "xiaohongshu": "小红书", "wechat": "公众号", "hotspot": "全网热点"}[name]
        try:
            items = collector(api_key, start_date, end_date)
            result["platforms"][name] = items
            result["totals"][name] = len(items)
            # Preview: show publishTime + title
            previews = []
            for i in items[:3]:
                pt = i.get("publishTime", i.get("gmtCreate", ""))
                pt_short = pt[5:16] if len(pt) > 10 else pt  # MM-DD HH:MM
                previews.append(f"[{pt_short}] {i['title'][:25]}...")
            preview = " | ".join(previews) if previews else "(无)"
            print(f"  [{label}] {len(items)} 条 → {preview}")
        except Exception as e:
            result["errors"].append({"platform": name, "error": str(e)})
            result["platforms"][name] = []
            result["totals"][name] = 0
            print(f"  [{label}] Failed: {e}")

    total = sum(result["totals"].values())
    print(f"  === 总计 {total} 条 AI 相关内容 ===\n")

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Output: {output_path}")

    return result


def main():
    api_key = os.environ.get("REDFOX_API_KEY", "")
    output = None
    start_date = ""
    end_date = ""

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        elif args[i] == "--start" and i + 1 < len(args):
            start_date = args[i + 1]
            i += 2
        elif args[i] == "--end" and i + 1 < len(args):
            end_date = args[i + 1]
            i += 2
        else:
            i += 1

    if not api_key:
        print("Error: REDFOX_API_KEY required. Set env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    result = collect_all(api_key, output, start_date, end_date)

    # Print JSON to stdout for piping
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
