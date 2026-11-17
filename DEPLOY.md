# 部署到 GitHub Pages（仓库名：finance-news）

> 3 步上线 + 每天北京时间 8:00 自动更新，全免费。

## 第 1 步：创建仓库

1. 打开 https://github.com/new
2. Repository name 填 `finance-news`
3. 选 **Public**（Pages 免费版公库最省事）
4. 不要勾选 Add a README（保持空仓库）
5. 点 **Create repository**

## 第 2 步：把网站推上去

把本机解压后的 `finance-news-website.zip` 内容推到仓库根目录。
仓库根目录应该是这样（`index.html` 必须在根目录）：

```
index.html
css/
js/
data/news.json
scripts/fetch_news.py
requirements.txt
.github/workflows/daily.yml
```

在解压目录里运行（把 YOURNAME 换成你的 GitHub 用户名）：

```bash
cd finance-news-website
git init
git add .
git commit -m "上线每日财经新闻站"
git branch -M main
git remote add origin https://github.com/YOURNAME/finance-news.git
git push -u origin main
```

如果提示要登录，按 GitHub 要求用 Token 或 GitHub Desktop 登录即可。
不想装 git？直接在仓库网页点 **Add file → Upload files**，把解压后的所有文件拖进去也行。

## 第 3 步：打开 Pages + 跑一次自动任务

1. 进仓库 **Settings → Pages**
2. Source 选 **Deploy from a branch**，Branch 选 **main** / **(root)**，点 Save
3. 等 1-2 分钟，访问 `https://YOURNAME.github.io/finance-news/` 就是你的网站
4. 进仓库 **Actions → 每日财经新闻自动收集 → Run workflow** 手动跑一次，确认是绿色 ✅
5. 之后每天北京时间 08:00 自动抓取并更新网站，不用管

## 验证清单

- [ ] `https://YOURNAME.github.io/finance-news/` 能打开
- [ ] Actions 跑过一次且为绿色
- [ ] 第二天 `data/news.json` 的 `updated_at` 自动变新

## 出问题怎么办

| 现象 | 解法 |
|---|---|
| Pages 显示 404 | 检查 `index.html` 是否在仓库根目录，而不是在子文件夹里；Pages 分支是否为 main/(root) |
| Actions 红色报错 | 点进去看日志，多半是网络超时，重跑一次即可 |
| 定时任务没跑 | GitHub 对长期无活动的仓库会暂停定时任务，进 Actions 点 Run workflow 唤醒一次即可 |
| 想换更新时间 | 改 `.github/workflows/daily.yml` 里的 `cron`，如 `0 22 * * *` = 北京时间次日 6:00 |

自定义域名：Pages 设置里填你的域名，再去域名商加一条 CNAME 到 `YOURNAME.github.io` 即可。
