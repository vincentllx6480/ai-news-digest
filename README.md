# AI 每日速递

> 每天 5 分钟，掌握 AI 行业全局 — 聚合国际大模型动态、国内AI产业进展、融资快讯与创业机会分析。

## 关于

AI 每日速递是由 Claude AI 驱动的自动化 AI 产业情报日报网站。

每天上午 9:10，系统自动从以下数据源采集最新资讯：
- **Claude WebSearch** — 国际新闻、融资动态、政策监管
- **RedFox Data API** — 抖音/小红书/公众号平台AI热点

LLM 对采集到的信息进行结构化分析，生成包含简报、关键信息、创业机会、指标追踪的完整日报。

## 技术架构

- **数据采集**: Python 3.11 + RedFox API + Claude WebSearch
- **AI 分析**: Claude / DeepSeek (OpenAI-compatible API)
- **前端**: 纯 HTML/CSS/JS (无框架，静态站点)
- **自动化**: macOS LaunchAgent 定时触发
- **部署**: Railway / GitHub Pages

## 目录结构

```
dist/           # 网站文件（部署根目录）
├── index.html  # 首页（最新日报）
├── archive/    # 历史归档
├── search.html # 全文搜索
├── trends.html # 趋势追踪
├── feed.xml    # RSS 订阅
├── data/       # JSON 数据
├── css/        # 样式
└── js/         # 脚本
scripts/        # 构建脚本
├── build_site.py      # 站点构建
├── collect_redfox.py  # 红狐数据采集
└── generate_feed.py   # RSS 生成
skills/         # Agent Skills
└── redfox-data-collector/
```

## 部署

### Railway

```bash
railway init
railway up
```

### GitHub Pages

Push `dist/` to `gh-pages` branch.

## License

MIT
