"""AI 每日速递 - 站点构建脚本

从 Claude 生成的 HTML 日报中提取内容，构建完整网站：
1. 生成首页（嵌入最新日报内容）
2. 更新归档索引
3. 生成搜索索引
4. 生成 RSS Feed
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(os.environ.get("SITE_DIR", os.path.expanduser("~/ai-news-digest-site")))
DIST_DIR = BASE_DIR / "docs"
DATA_DIR = DIST_DIR / "data"
ARCHIVE_DIR = DIST_DIR / "archive"
DESKTOP_FILE = Path(os.environ.get("DESKTOP", os.path.expanduser("~/Desktop")))

def get_today_str():
    return datetime.now().strftime("%m%d")

def get_date_display():
    now = datetime.now()
    return f"{now.month:02d}.{now.day:02d}"

def extract_report_content(html_path: Path) -> dict:
    """从 Claude 生成的 HTML 中提取关键内容块"""
    if not html_path.exists():
        return None

    content = html_path.read_text(encoding='utf-8')

    # Extract title
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else "AI 每日速递"

    # Extract meta description
    desc_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', content)
    description = desc_match.group(1) if desc_match else ""

    # Extract main content sections (heuristic: body content between header and footer)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    body = body_match.group(1) if body_match else content

    # Extract headlines/summaries for search index
    headlines = []
    for m in re.finditer(r'<h[234][^>]*>(.*?)</h[234]>', body, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) > 5:
            headlines.append(text)

    # Extract tags/keywords
    tags = []
    tag_section = re.findall(r'(OpenAI|Anthropic|Google|DeepSeek|智谱|阿里|字节|腾讯|Kimi|GPT|Claude|Gemini|大模型|融资|IPO|Agent)', content)
    tags = list(set(tag_section))[:15]

    return {
        "title": title,
        "description": description[:200],
        "headlines": headlines[:20],
        "tags": tags,
        "date": get_today_str(),
        "dateDisplay": get_date_display(),
    }


def update_archive_index(date_str: str, metadata: dict):
    """更新归档索引"""
    index_path = DATA_DIR / "index.json"

    if index_path.exists():
        index = json.loads(index_path.read_text(encoding='utf-8'))
    else:
        index = {"dates": [], "lastUpdated": ""}

    # Check if date already exists
    existing = [d for d in index["dates"] if d["date"] == date_str]
    if existing:
        existing[0].update({
            "title": metadata.get("title", ""),
            "tags": metadata.get("tags", []),
        })
    else:
        index["dates"].append({
            "date": date_str,
            "title": metadata.get("title", ""),
            "headlines": metadata.get("headlines", [])[:8],
            "tags": metadata.get("tags", []),
        })

    index["dates"].sort(key=lambda x: x["date"], reverse=True)
    index["lastUpdated"] = datetime.now().isoformat()

    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')


def update_search_index(metadata: dict):
    """更新搜索索引"""
    search_path = DATA_DIR / "search-index.json"

    if search_path.exists():
        sindex = json.loads(search_path.read_text(encoding='utf-8'))
    else:
        sindex = []

    date_str = metadata.get("date", "")

    # Remove existing entries for this date
    sindex = [s for s in sindex if s.get("date") != date_str]

    # Add headlines as searchable items
    for hl in metadata.get("headlines", []):
        sindex.append({
            "date": date_str,
            "title": hl,
            "summary": metadata.get("description", ""),
            "source": "AI速递",
            "tags": metadata.get("tags", []),
            "url": f"/archive/{date_str}.html"
        })

    search_path.write_text(json.dumps(sindex, ensure_ascii=False, indent=2), encoding='utf-8')


def archive_report(date_str: str, source_html: Path):
    """归档 HTML 报告到 dist/archive/"""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / f"{date_str}.html"

    if source_html.exists():
        shutil.copy2(source_html, dest)
        print(f"  Archived: {dest}")
        return True
    return False


def generate_rss():
    """生成 RSS Feed"""
    index_path = DATA_DIR / "index.json"
    if not index_path.exists():
        return

    index = json.loads(index_path.read_text(encoding='utf-8'))
    dates = sorted(index.get("dates", []), key=lambda x: x["date"], reverse=True)

    items = []
    for d in dates[:30]:
        date_str = d["date"]
        y = "20" + date_str[:2]
        m = date_str[2:4]
        day = date_str[4:6]
        pub_date = f"{y}-{m}-{day}T09:10:00+08:00"

        items.append(f"""    <item>
      <title>{d.get('title', 'AI 每日速递 ' + date_str)}</title>
      <link>https://ai-digest.paicoding.com/archive/{date_str}.html</link>
      <guid>https://ai-digest.paicoding.com/archive/{date_str}.html</guid>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{d.get('description', '')[:500]}]]></description>
    </item>""")

    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AI 每日速递</title>
    <link>https://ai-digest.paicoding.com</link>
    <description>每日AI产业资讯聚合：国际大模型动态、国内AI进展、融资快讯、创业机会分析</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="https://ai-digest.paicoding.com/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

    (DIST_DIR / "feed.xml").write_text(rss, encoding='utf-8')
    print("  RSS feed generated: dist/feed.xml")


def build_site():
    """主构建流程"""
    print(f"[{datetime.now():%H:%M:%S}] Building site...")

    today = get_today_str()

    # Find today's report
    source = DESKTOP_FILE / f"今天{today}AI速递.html"

    if source.exists():
        print(f"  Source: {source}")
        metadata = extract_report_content(source)

        if metadata:
            # Copy as index.html for the site
            dest_index = DIST_DIR / "index.html"
            shutil.copy2(source, dest_index)
            print(f"  Index updated: {dest_index}")

            # Archive
            archive_report(today, source)

            # Update indices
            update_archive_index(today, metadata)
            update_search_index(metadata)
            generate_rss()

            print(f"  Site built successfully for {today}")
        else:
            print("  Warning: Could not extract metadata from report")
    else:
        print(f"  No report found at {source}")
        print("  Site index.html unchanged")


def init_site():
    """初始化站点目录和基础文件"""
    dirs = [
        DIST_DIR, DATA_DIR, ARCHIVE_DIR,
        DIST_DIR / "css", DIST_DIR / "js", DIST_DIR / "assets"
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Ensure data files exist
    if not (DATA_DIR / "index.json").exists():
        (DATA_DIR / "index.json").write_text('{"dates":[],"lastUpdated":""}', encoding='utf-8')
    if not (DATA_DIR / "search-index.json").exists():
        (DATA_DIR / "search-index.json").write_text('[]', encoding='utf-8')

    print("Site initialized.")


if __name__ == "__main__":
    init_site()
    build_site()
