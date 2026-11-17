# 每日财经新闻网站 📰

每天自动收集财经新闻的聚合网站,开箱即用。

## 功能

- ✅ 每天自动抓取 16 个财经 RSS 源(中国 10 个 + 全球 6 个)
- ✅ 两级分类:地区(🇨🇳中国 / 🌍全球)× 板块(宏观政策 / 股市 / 科技 / 汽车出行 / 医疗健康 / 贵金属 / 能源 / 基金理财 / 房地产 / 综合)
- ✅ 搜索 + 分类 + 中英文 + 日期筛选 + 排序
- ✅ 深色模式 + 响应式(手机/电脑自适应)
- ✅ 每日归档 `data/history/YYYY-MM-DD.json`,保留 60 天
- ✅ GitHub Actions 每天北京时间 8:00 自动更新

## 目录结构

```
finance-news-website/
├── index.html                  # 网站首页
├── css/style.css               # 样式
├── js/app.js                   # 前端逻辑
├── data/news.json              # 最新新闻数据(自动生成)
├── data/history/               # 每日归档(自动生成)
├── scripts/fetch_news.py       # 每日抓取脚本
├── requirements.txt
└── .github/workflows/daily.yml # 每日定时任务
```

## 快速开始

### 1. 本地预览(已内置 146 条真实新闻,直接打开即可)

```bash
cd finance-news-website
python -m http.server 8000
# 浏览器访问 http://localhost:8000
```

> ⚠️ 不要用 `file://` 直接双击打开(浏览器会拦截 data/news.json 读取),一定要用上面的本地服务器方式。

### 2. 手动更新新闻(每天运行一次)

```bash
pip install -r requirements.txt
python scripts/fetch_news.py
```

Windows 可双击 `run.bat`,Mac/Linux 运行 `bash run.sh`。

### 3. 部署到网上(实现每天自动收集)

**方法 A:GitHub Pages + Actions(推荐,全免费)**

1. 把本目录推到 GitHub 仓库
2. 仓库 Settings → Pages → Source 选 `Deploy from a branch`,分支选 `main`、目录选 `/ (root)` 或 `/finance-news-website`
3. `Actions` 里点 `每日财经新闻自动收集` → `Run workflow` 手动跑一次
4. 之后每天北京时间 8:00 自动抓取并更新网站

**方法 B:定时任务(自己的电脑/服务器)**

```bash
# Linux/Mac 每天 8:00 执行
crontab -e
0 8 * * * cd /path/to/finance-news-website && python3 scripts/fetch_news.py
```

### 4. 添加/删除新闻源

编辑 `scripts/fetch_news.py` 顶部的 `SOURCES` 数组,加一行 RSS 地址即可:

```python
{"name": "我的来源", "url": "https://xxx/rss.xml", "lang": "zh"},
```

## 常见问题

- **英文新闻看不懂?** 站内搜索支持中英文关键词,英文标题点击"阅读原文"后可用浏览器自带翻译。
- **想只看中文?** 顶部筛选器选"中文"即可。
- **数据源版权**:RSS 为各站公开资讯,本站仅做聚合展示,版权归原站所有。

## 许可

MIT,可自由修改商用。
