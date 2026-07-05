import json

from . import config, llm

SYSTEM = """你是一名开源社区沟通高手。基于给定的仓库和提案，生成两类发布草稿：

1. PR 描述（英文）：title + body。body 包含 Motivation（引用相关 issue）、What changed、How tested、Checklist。语气谦逊专业，尊重 maintainer 的时间，不居高临下。
2. 三条 X（Twitter）帖子草稿（英文），风格分别为 technical（讲清技术点）、story（讲发现问题到解决的过程）、short（一两句 + 链接）。要求：如实署名原项目并给出原仓库链接位置（用 <repo-url> 占位）；只描述真实完成的工作，不夸大；最多 2 个话题标签。

输出 JSON：
{"pr": {"title": "...", "body": "..."},
 "posts": [{"style": "technical", "text": "..."},
           {"style": "story", "text": "..."},
           {"style": "short", "text": "..."}]}

注意：这些只是草稿，正文假设改动已完成且测试通过——发布前必须由人核对事实、手动发出。"""


def draft(full, index):
    d = config.report_dir(full)
    proposals_path = d / "proposals.json"
    if not proposals_path.exists():
        raise RuntimeError("还没有提案，先运行: oss-scout propose " + full)
    result = json.loads(proposals_path.read_text(encoding="utf-8"))
    proposals = result.get("proposals", [])
    if not 1 <= index <= len(proposals):
        raise RuntimeError("提案编号 {} 超出范围（共 {} 个）".format(index, len(proposals)))
    proposal = proposals[index - 1]

    user = "仓库: {}（https://github.com/{}）\n提案:\n{}".format(
        full, full, json.dumps(proposal, ensure_ascii=False, indent=2)
    )
    data = llm.ask_json(SYSTEM, user)

    lines = [
        "# 发布草稿：{} — 提案 {}".format(full, index),
        "",
        "> ⚠️ 仅为草稿。PR 由人 review 代码后手动 `gh pr create`；帖子由人核对事实后手动发布。",
        "",
        "## PR 标题",
        "",
        data.get("pr", {}).get("title", ""),
        "",
        "## PR 正文",
        "",
        data.get("pr", {}).get("body", ""),
        "",
    ]
    for p in data.get("posts", []):
        lines += ["## X 草稿（{}）".format(p.get("style", "")), "", p.get("text", ""), ""]

    path = d / "drafts_{}.md".format(index)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
