#!/usr/bin/env python3
"""RedFox Data Collector - 红狐数据 API 采集脚本

从红狐数据 API 采集抖音/小红书/公众号三平台的 AI 相关热点数据。

API 文档: https://redfox.hk
认证方式: X-API-KEY 请求头

用法:
    python3 collect.py --api-key YOUR_KEY [--output data.json]
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

REDFOX_BASE = "https://redfox.hk/story/api"

# 平台采集配置
PLATFORMS = {
    "douyin": {
        "search": f"{REDFOX_BASE}/dyData/searchWork",
        "detail": f"{REDFOX_BASE}/dyData/queryWork",
        "keywords": ["AI", "人工智能", "大模型"],
        "label": "抖音",
    },
    "xiaohongshu": {
        "search": f"{REDFOX_BASE}/xhsData/queryWork",
        "keywords": ["AI工具", "AI编程", "AI智能体", "Agent", "大模型"],
        "label": "小红书",
    },
    "wechat": {
        "search": f"{REDFOX_BASE}/gzhData/searchArticle",
        "keywords": ["AI工具", "AI编程", "AI智能体", "Agent", "大模型"],
        "label": "公众号",
    },
}


def call_api(url: str, payload: dict, api_key: str, timeout: int = 15) -> dict:
    """调用红狐数据 API"""
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


def collect_douyin(api_key: str) -> list:
    """采集抖音 AI 相关热门作品"""
    results = []
    cfg = PLATFORMS["douyin"]

    for keyword in cfg["keywords"]:
        try:
            resp = call_api(cfg["search"], {
                "keyword": keyword,
                "offset": 0,
                "count": 5,
            }, api_key)

            if resp.get("code") == 2000:
                for item in resp.get("data", {}).get("list", [])[:3]:
                    results.append({
                        "platform": "douyin",
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "likeCount": item.get("likeCount", 0),
                        "commentCount": item.get("commentCount", 0),
                        "shareCount": item.get("shareCount", 0),
                        "collectCount": item.get("collectCount", 0),
                        "workUrl": item.get("workUrl", ""),
                        "coverUrl": item.get("coverUrl", ""),
                        "keyword": keyword,
                    })
            time.sleep(0.2)  # Rate limiting
        except Exception as e:
            print(f"  [Douyin Error] keyword={keyword}: {e}", file=sys.stderr)

    return results[:5]


def collect_xiaohongshu(api_key: str) -> list:
    """采集小红书 AI 相关爆款笔记"""
    results = []
    cfg = PLATFORMS["xiaohongshu"]

    for keyword in cfg["keywords"]:
        try:
            resp = call_api(cfg["search"], {
                "keyword": keyword,
                "sortType": "_4",  # 按热度
                "offset": 0,
            }, api_key)

            if resp.get("code") == 2000:
                for item in resp.get("data", {}).get("list", [])[:2]:
                    results.append({
                        "platform": "xiaohongshu",
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "likeCount": item.get("likeCount", 0),
                        "commentCount": item.get("commentCount", 0),
                        "collectCount": item.get("collectCount", 0),
                        "workUrl": item.get("workUrl", ""),
                        "coverUrl": item.get("coverUrl", ""),
                        "keyword": keyword,
                    })
            time.sleep(0.2)
        except Exception as e:
            print(f"  [XHS Error] keyword={keyword}: {e}", file=sys.stderr)

    return results[:5]


def collect_wechat(api_key: str) -> list:
    """采集公众号 AI 相关热门文章"""
    results = []
    cfg = PLATFORMS["wechat"]

    for keyword in cfg["keywords"]:
        try:
            resp = call_api(cfg["search"], {
                "keyword": keyword,
                "offset": 0,
                "sortType": "_4",  # 按阅读数倒序
            }, api_key)

            if resp.get("code") == 2000:
                for item in resp.get("data", {}).get("list", [])[:2]:
                    results.append({
                        "platform": "wechat",
                        "title": item.get("title", ""),
                        "author": item.get("author", ""),
                        "readCount": item.get("readCount", 0),
                        "likeCount": item.get("likeCount", 0),
                        "commentCount": item.get("commentCount", 0),
                        "shareCount": item.get("shareCount", 0),
                        "workUrl": item.get("workUrl", ""),
                        "publishTime": item.get("publishTime", ""),
                        "keyword": keyword,
                    })
            time.sleep(0.2)
        except Exception as e:
            print(f"  [WeChat Error] keyword={keyword}: {e}", file=sys.stderr)

    return results[:5]


def collect_all(api_key: str, output_path: str = None) -> dict:
    """采集所有平台数据"""
    print(f"[{datetime.now():%H:%M:%S}] RedFox Data Collection Started")

    result = {
        "collectedAt": datetime.now().isoformat(),
        "platforms": {},
        "errors": [],
        "totals": {"douyin": 0, "xiaohongshu": 0, "wechat": 0},
    }

    # 并行采集（顺序执行但独立容错）
    for name, collector in [
        ("douyin", collect_douyin),
        ("xiaohongshu", collect_xiaohongshu),
        ("wechat", collect_wechat),
    ]:
        try:
            items = collector(api_key)
            result["platforms"][name] = items
            result["totals"][name] = len(items)
            print(f"  [{PLATFORMS[name]['label']}] Collected {len(items)} items")
        except Exception as e:
            result["errors"].append({"platform": name, "error": str(e)})
            result["platforms"][name] = []
            print(f"  [{PLATFORMS[name]['label']}] Failed: {e}")

    total = sum(result["totals"].values())
    print(f"  Total: {total} items across {len(result['platforms'])} platforms")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Output: {output_path}")

    return result


def main():
    api_key = os.environ.get("REDFOX_API_KEY", "")
    output = None

    # Parse CLI args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        else:
            i += 1

    if not api_key:
        print("Error: REDFOX_API_KEY required. Set env var or use --api-key", file=sys.stderr)
        sys.exit(1)

    result = collect_all(api_key, output)

    # Print JSON to stdout for piping
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
