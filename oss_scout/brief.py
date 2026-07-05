import json

from . import config, db, llm

SYSTEM = """你是一名工程 tech lead。基于给定的仓库分析和选定的提案，为一个 coding agent（Claude Code）写一份实施简报（中文 Markdown）。简报必须独立成篇——执行者看不到本对话，只看简报和代码。

结构：
# 实施简报：<repo> — <提案标题>
## 背景
两三句：项目是什么、这个改动为什么有价值，引用 issue 编号。
## 任务范围
做什么、明确不做什么（防止 scope 膨胀）。
## 验收标准
可执行、可验证。
## 实施建议
可能涉及的模块/文件方向、要注意的坑；材料里看不出来的标注"需现场确认"。
## 流程约束
- 先读 CONTRIBUTING.md 和现有代码风格，遵守上游规范
- 改动最小化，必须带测试，本地测试全绿再提交
- commit message 遵循上游惯例
- 完成后停在 draft PR 之前，等人工 review diff"""


def build_brief(full, index):
    d = config.report_dir(full)
    proposals_path = d / "proposals.json"
    if not proposals_path.exists():
        raise RuntimeError("还没有提案，先运行: oss-scout propose " + full)
    result = json.loads(proposals_path.read_text(encoding="utf-8"))
    proposals = result.get("proposals", [])
    if not 1 <= index <= len(proposals):
        raise RuntimeError("提案编号 {} 超出范围（共 {} 个）".format(index, len(proposals)))
    proposal = proposals[index - 1]
    assessment = (d / "assessment.md").read_text(encoding="utf-8")

    user = "仓库: {}\n\n选定提案:\n{}\n\n完整分析报告:\n{}".format(
        full, json.dumps(proposal, ensure_ascii=False, indent=2), assessment
    )
    brief = llm.ask(SYSTEM, user)

    path = d / "brief_{}.md".format(index)
    name = full.split("/")[-1]
    footer = """

---
## 交给 Claude Code 执行

```bash
gh repo fork {full} --clone && cd {name}
git checkout -b oss-scout/proposal-{index}
claude "$(cat '{brief_path}')"
```

实施完成、本地测试通过、人工 review 过 diff 之后，再手动 `gh pr create`。
""".format(full=full, name=name, index=index, brief_path=path)

    path.write_text(brief + footer, encoding="utf-8")
    con = db.connect()
    with con:
        db.set_status(con, full, "briefed")
    con.close()
    return path
