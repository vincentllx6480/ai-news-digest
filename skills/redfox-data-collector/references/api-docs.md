# RedFox Data API Reference

## Base URL
```
https://redfox.hk/story/api
```

## Authentication
All requests require `X-API-KEY` header. Get your free API key at https://redfox.hk

## API Endpoints

### 公众号 (WeChat)

#### Search Articles
```
POST /gzhData/searchArticle
Body: { "keyword": "AI", "offset": 0, "sortType": "_4" }
```
sortType: `_4` = by reads desc, `_2` = by publish time desc

#### Search Accounts
```
POST /gzhData/searchAccount
Body: { "keyword": "name" }
```

#### Query Work Detail
```
POST /gzhData/queryWork
Body: { "uuid": "..." }
```

### 小红书 (Xiaohongshu)

#### Query Account
```
POST /xhsData/queryAccount
Body: { "accountId": "..." }
```

#### Query Work
```
POST /xhsData/queryWork
Body: { "keyword": "AI工具", "sortType": "_4", "offset": 0 }
```

### 抖音 (Douyin)

#### Search Works
```
POST /dyData/searchWork
Body: { "keyword": "AI", "offset": 0, "count": 5 }
```

#### Query Work Detail
```
POST /dyData/queryWork
Body: { "workId": "..." }
```

## Response Format
```json
{
  "code": 2000,
  "msg": "成功",
  "data": {
    "total": 100,
    "hasMore": true,
    "list": [...]
  }
}
```

## Rate Limits
- ~60 requests/minute
- Add minimum 150ms delay between requests
