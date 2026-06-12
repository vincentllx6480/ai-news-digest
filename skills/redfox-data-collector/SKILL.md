---
name: redfox-data-collector
description: 红狐数据 API 采集器 - 从抖音/小红书/公众号采集 AI 热点数据
version: 1.0.0
author: Lin Lixiao
created: 2026-06-12
---

# RedFox Data Collector Skill

## Overview

This Skill collects AI-related trending content from Douyin (抖音), Xiaohongshu (小红书), and WeChat Public Accounts (公众号) via the RedFox Data API, and outputs structured JSON for LLM analysis.

## Data Sources

### RedFox Data API (redfox.hk)

A developer-oriented new media data platform providing structured data from 7 Chinese social platforms.

**Authentication:** X-API-KEY header (free registration at redfox.hk)

**API Categories:**
- 公众号 (WeChat): 6 endpoints - account search, article search, account info, article detail, work list, URL lookup
- 小红书 (Xiaohongshu): 2 endpoints - account detail, work detail
- 抖音 (Douyin): 2 endpoints - account detail, work detail
- 工具类 (Tools): AI image generation (image2-GPT), video generation (Seendance 2.0), image gen (Seedream 5.0 lite)

## Collection Strategy

### Platform 1: Douyin (抖音)
- **Search keywords:** AI, 人工智能, 大模型
- **Method:** Keyword search + work detail enrichment
- **Data points:** Title, author, likes, comments, shares, favorites, comment hot words
- **Target:** 5 items per run

### Platform 2: Xiaohongshu (小红书)
- **Search keywords:** AI工具, AI编程, AI智能体, Agent, 大模型
- **Method:** Hot content query sorted by engagement
- **Data points:** Title, author, likes, comments, collects, cover image
- **Target:** 5 items per run

### Platform 3: WeChat Public Accounts (公众号)
- **Search keywords:** AI工具, AI编程, AI智能体, Agent, 大模型
- **Method:** Article search sorted by read count (_4)
- **Data points:** Title, author, reads, likes, comments, shares, publish time
- **Target:** 5 items per run

## Fault Tolerance

- Single platform failure does not affect other platforms
- Each platform has a fallback keyword set
- 0.15-0.25s delay between API calls to respect rate limits
- All errors captured in `errors[]` array in output

## Usage

### CLI
```bash
python3 scripts/collect.py --api-key YOUR_KEY --output data/redfox_latest.json
```

### Environment Variable
```bash
export REDFOX_API_KEY=ak_your_key
python3 scripts/collect.py --output data/redfox_latest.json
```

### In Agent (Claude Code / Codex)
The Skill can be loaded by any Agent that supports the Skill format. The Agent reads this SKILL.md for collection strategy and API parameters, then executes `scripts/collect.py` with the configured API key.

## Output Format

```json
{
  "collectedAt": "2026-06-12T09:10:00+08:00",
  "platforms": {
    "douyin": [...],
    "xiaohongshu": [...],
    "wechat": [...]
  },
  "errors": [],
  "totals": {"douyin": 5, "xiaohongshu": 5, "wechat": 5}
}
```

## Integration Points

This Skill feeds data into:
1. **AI 每日速递 Daily Report** - Platform data panels
2. **LLM Opportunity Scorer** - Input for opportunity analysis
3. **Trend Tracker** - Historical engagement metrics
