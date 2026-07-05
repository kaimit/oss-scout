# oss-scout web · agent 项目审阅仪表盘

Next.js 审阅仪表盘：实时列 AI agent 领域候选项目，展示本地生成的优化提案，你在网页勾选确认；实际优化和发布回本地 + 人工。

## 本地预览

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

`/api/discover` 用 GitHub search 实时抓 agent 候选。设 `GITHUB_TOKEN` 环境变量可把 API 限额从 60 提到 5000 次/小时。

## 让网页显示已分析项目

"已生成分析"区来自 `web/data/reports.json`，由本地 CLI 导出：

```bash
cd ..                                   # 回 oss-scout 根目录
.venv/bin/oss-scout analyze owner/repo
.venv/bin/oss-scout propose owner/repo
.venv/bin/oss-scout export              # 写 web/data/reports.json
```

## 部署到 Vercel

1. 代码已在 GitHub（kaimit/oss-scout）
2. vercel.com → Add New → Project → 选 `kaimit/oss-scout`
3. **Root Directory 设为 `web`**
4. Environment Variables 加 `GITHUB_TOKEN`（classic PAT，勾 `public_repo` 即可）
5. Deploy

深度分析（analyze/propose）**不在 web 跑**——serverless 有超时，且优化/发布需人工把关。网页只做发现 + 审阅 + 确认。
