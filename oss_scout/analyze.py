import json
from datetime import datetime, timezone

from . import config, db, github_api, llm

SYSTEM = """你是一名资深开源工程师兼产品分析师。基于给定的 GitHub 仓库资料（元数据、README、高热度 issue、文件结构样本），写一份简洁但有洞察的中文分析报告，Markdown 格式，包含以下小节：

## 项目定位
它解决什么问题，一句话说清。

## 目标用户与使用场景

## 用户真实痛点
基于 issue 证据，引用编号（如 #123）。区分"用户抱怨的"和"你推测的"。

## 差距与机会
从测试覆盖、性能、文档、错误信息、生态集成、易用性等维度找**具体的、单个 PR 能装下的**改进点，不要泛泛而谈。

## 维护活跃度与社区状态

## 一句话结论
这个项目值不值得投入贡献、最值得做的一件事是什么。

要求：所有结论必须锚定给定材料中的证据；材料里看不出来的就明说"材料不足，需 clone 后确认"。"""


def build_context(full):
    info = github_api.repo_info(full)
    branch = info.get("default_branch", "main")
    readme = github_api.readme(full)
    issues = github_api.top_issues(full)
    langs = github_api.languages(full)
    tree, truncated = github_api.file_tree(full, branch)

    pushed = info.get("pushed_at", "")
    days_since_push = None
    if pushed:
        try:
            dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days_since_push = (datetime.now(timezone.utc) - dt).days
        except ValueError:
            pass

    license_obj = info.get("license") or {}
    meta = {
        "full_name": info.get("full_name", full),
        "description": info.get("description") or "",
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "open_issues": info.get("open_issues_count", 0),
        "topics": info.get("topics", []),
        "license_spdx": license_obj.get("spdx_id") or "NONE",
        "pushed_at": pushed,
        "days_since_push": days_since_push,
        "default_branch": branch,
        "languages": langs,
    }

    issues_text = "\n\n".join(
        "- #{}（{} 条评论）{}\n  {}".format(
            i["number"], i["comments"], i["title"], i["body"][:400]
        )
        for i in issues
    ) or "（没有拿到 open issue）"

    parts = [
        "# 仓库元数据\n" + json.dumps(meta, ensure_ascii=False, indent=2),
        "# README（截断至 10000 字符）\n" + (readme[:10000] or "（无 README）"),
        "# 高热度 open issues（按评论数排序）\n" + issues_text,
        "# 文件结构样本{}\n".format("（已截断）" if truncated else "") + "\n".join(tree[:200]),
    ]
    return meta, "\n\n".join(parts)


def analyze(full):
    meta, context = build_context(full)
    report = llm.ask(SYSTEM, context)
    d = config.report_dir(full)
    (d / "assessment.md").write_text(report, encoding="utf-8")
    (d / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    con = db.connect()
    with con:
        db.set_status(con, full, "analyzed")
    con.close()
    return meta, report
