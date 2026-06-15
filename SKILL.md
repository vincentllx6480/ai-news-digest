---
name: ai-news-digest-site
description: AI速递 - 每日AI新闻简报自动化站点。从红狐数据API采集抖音/小红书/公众号/全网热点四平台AI数据，通过Claude生成HTML简报，自动部署到GitHub Pages。支持分类Tab切换、归档检索、RSS订阅、定时任务推送。触发词：AI速递、AI新闻、AI日报、AI简报、AI热点、AI trends。
---

# AI速递 - 每日AI新闻自动化简报

## 简介

每日自动采集抖音、小红书、公众号、全网热点四平台的AI相关热点内容，通过Claude生成精美的HTML新闻简报页面，自动部署到GitHub Pages。支持首页分类Tab切换、历史归档、全文搜索、RSS订阅和每日定时推送。

## 工作流程

1. **数据采集** (`scripts/collect_redfox.py`)：从红狐API采集四平台AI数据
2. **内容生成** (Claude)：基于采集数据+AI动态生成新闻简报
3. **站点构建** (`scripts/build_site.py`)：生成首页、归档页、更新搜索索引
4. **自动部署** (git push)：推送至GitHub Pages自动发布

## 关键路径

- 站点目录：`docs/`
- 采集脚本：`scripts/collect_redfox.py`
- 构建脚本：`scripts/build_site.py`
- 定时任务：`~/.claude/ai-news-digest.sh` (LaunchAgent 每天 9:10)
- API配置：`REDFOX_API_KEY` 环境变量
- 站点地址：`https://vincentllx6480.github.io/ai-news-digest/`
