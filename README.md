# oss-scout

从 GitHub trending 发现项目 → 理解真实需求 → 生成可落地的优化提案、实施简报和发布草稿。

**设计原则：贡献优先（upstream PR），一切对外发布动作前置人工把关。** 机器负责发现、分析、提案、写草稿（约 90% 的工作量）；人负责判断和发布（决定做哪个、review 代码、点下发送）。

## 为什么不做"自动 fork + 优化 + 另发仓库 + 自动推广"

1. **许可证**：trending 项目里相当比例没有 LICENSE（法律上默认保留所有权利，再发布即侵权），或是 GPL/AGPL 等 copyleft（衍生物必须同许可证）。全自动管道会批量踩雷。
2. **平台规则**：GitHub 的 spam / inauthentic activity 政策与 X 的平台操纵规则都禁止大规模自动化复制内容和自动推广，触发后限流或封号。
3. **社区口碑**：开源社区对 "AI slop"（低质自动生成的 PR 和克隆仓库）极其敏感，被点名的账号基本告别社区。反过来，真实的 merged PR + 如实的分享帖，是涨 star 和 followers 最有效的路径。

因此本产品把"优化成果"默认导向 **给原仓库提 PR**；只有当产物是独立的新东西（插件、SDK、基准测试等）且许可证允许时，才走"伴生项目"路线——且永远不做"整仓 fork 改名再发布"。

## 管道

```
discover ──▶ analyze ──▶ propose ──▶ brief ──▶ (Claude Code 实施) ──▶ draft ──▶ 人工发布
 抓trending   LLM需求评估   提案+许可证把关   实施简报      写代码+测试        PR/帖子草稿   review后手动发
 [自动]       [自动]        [自动]          [自动]        [半自动]           [自动]       [人工 gate]
```

## 快速开始

```bash
cd oss-scout
python3 -m venv .venv
.venv/bin/pip install -U pip && .venv/bin/pip install -e .
cp .env.example .env   # 填入 ANTHROPIC_API_KEY（GITHUB_TOKEN 可选）

# 端到端跑一轮：发现 → 分析 → 提案
.venv/bin/oss-scout run --language python --top 3
```

## 命令

| 命令 | 作用 |
|---|---|
| `oss-scout discover [-l python] [--since daily]` | 抓 GitHub trending，入候选池（页面结构变化时自动回退 search API） |
| `oss-scout list` | 查看候选池与各仓库处理状态 |
| `oss-scout analyze owner/repo` | 拉取 README / 高热度 issues / 文件结构，LLM 生成需求评估报告 |
| `oss-scout propose owner/repo` | 生成 3-5 个优化提案；自动做许可证检查与策略把关 |
| `oss-scout brief owner/repo -p N` | 为第 N 个提案生成实施简报，末尾附可直接执行的 Claude Code 命令 |
| `oss-scout draft owner/repo -p N` | 生成英文 PR 描述 + 三条 X 帖子草稿（只写文件，不发布） |
| `oss-scout run [-l python] [--top 3]` | discover → 逐个 analyze + propose，端到端一轮 |

产物都在 `data/reports/<owner>__<repo>/` 下：`assessment.md`、`proposals.md`、`brief_N.md`、`drafts_N.md`。

## 许可证把关逻辑

- **无 LICENSE / NOASSERTION** → 只允许 upstream PR，companion 提案自动降级
- **Copyleft（GPL/AGPL/LGPL/MPL/EPL）** → companion 必须同许可证，提案里明确标注
- **宽松（MIT/Apache-2.0/BSD…）** → companion 允许，需保留版权声明
- **近 60 天有提交** → 标注"上游活跃，优先 PR"

## 实施与发布（人工环节）

`brief` 生成的简报末尾带一段命令：fork + clone + 开分支 + 把简报喂给 Claude Code。代码写完、测试通过后，**人 review diff，手动 `gh pr create`**；X 帖子从 `drafts_N.md` 里挑一条核对事实后手动发。

## Roadmap

- [ ] 定时运行：`claude schedule` 或 cron 每天跑 `oss-scout run`，早上看提案挑活
- [ ] `gh pr create` 集成（带确认交互）
- [ ] 效果追踪：记录提了哪些 PR、merge 率、star/follower 变化
- [ ] X API 发布（带确认交互，替代手动贴）
- [ ] 用 Claude Agent SDK 把 brief → 实施做成受控自动步骤

## 配置

`.env`（见 `.env.example`）：`ANTHROPIC_API_KEY`（必需）、`GITHUB_TOKEN`（可选，提额度）、`OSS_SCOUT_MODEL`（默认 `claude-opus-4-8`）。
