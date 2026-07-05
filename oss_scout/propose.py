import json

from . import config, db, llm

PERMISSIVE = {
    "MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC",
    "UNLICENSE", "0BSD", "CC0-1.0", "ZLIB",
}
COPYLEFT_PREFIXES = ("GPL", "AGPL", "LGPL", "MPL", "EPL")

SYSTEM = """你是一名资深开源 maintainer。基于分析报告，为该仓库生成 3-5 个"值得做、做得动、上游愿意收"的优化提案。

硬性规则：
1. strategy 只能是 "upstream_pr"（默认：把优化以 PR 贡献回原仓库）或 "companion_project"（独立新工件：插件、SDK、集成、基准测试套件等）。
2. 绝不提出"fork 整个仓库、优化后另发一个仓库"这类提案——那不是贡献，是生态碎片化。
3. companion_project 仅当产物是原仓库没有、也不适合放进原仓库的独立新东西。
4. 每个提案必须锚定分析报告中的证据（issue 编号或报告明确指出的差距）。
5. 提案要小而锋利：一个 PR 能装下、maintainer 一眼能看懂价值。修一个高热度 bug 胜过重构半个项目。

输出 JSON：
{"proposals": [{
  "title": "简短标题",
  "strategy": "upstream_pr 或 companion_project",
  "type": "perf | bugfix | tests | docs | feature | tooling | integration",
  "impact": 1 到 5 的整数,
  "effort": "S | M | L",
  "rationale": "为什么值得做（中文，两三句）",
  "evidence": "锚定的 issue 编号或报告中的差距",
  "acceptance_criteria": ["可验证的验收标准"]
}]}"""


def license_policy(spdx, days_since_push):
    spdx_up = (spdx or "NONE").upper()
    no_license = spdx_up in {"NONE", "NOASSERTION"}
    copyleft = any(spdx_up.startswith(p) for p in COPYLEFT_PREFIXES)

    policy = {
        "spdx": spdx or "NONE",
        "allow_upstream_pr": True,
        "allow_companion": not no_license,
        "companion_must_same_license": copyleft,
        "notes": [],
    }
    if no_license:
        policy["notes"].append(
            "仓库未声明开源许可证 = 默认保留所有权利。包含其代码的衍生/伴生项目属于侵权，只能走 upstream PR。"
        )
    elif copyleft:
        policy["notes"].append(
            "Copyleft 许可证（{}）：衍生作品必须使用相同许可证并保留版权声明。".format(spdx)
        )
    elif spdx_up in PERMISSIVE:
        policy["notes"].append(
            "宽松许可证（{}）：衍生作品需保留原版权与许可声明。".format(spdx)
        )
    else:
        policy["notes"].append(
            "许可证 {} 不在常见清单内，动手前人工确认条款。".format(spdx)
        )
    if days_since_push is not None and days_since_push <= 60:
        policy["notes"].append("上游活跃维护中：优先 upstream PR，避免生态碎片化。")
    return policy


def propose(full):
    d = config.report_dir(full)
    assessment_path = d / "assessment.md"
    if not assessment_path.exists():
        raise RuntimeError("还没有分析报告，先运行: oss-scout analyze " + full)
    assessment = assessment_path.read_text(encoding="utf-8")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    policy = license_policy(meta.get("license_spdx"), meta.get("days_since_push"))

    user = "仓库: {}\n许可证策略: {}\n\n分析报告:\n{}".format(
        full, json.dumps(policy, ensure_ascii=False), assessment
    )
    data = llm.ask_json(SYSTEM, user)
    proposals = data.get("proposals", [])

    # 硬性把关：许可证不允许衍生物时，companion 提案一律降级为 upstream PR
    for p in proposals:
        if p.get("strategy") == "companion_project" and not policy["allow_companion"]:
            p["strategy"] = "upstream_pr"
            p["license_note"] = "原提案为 companion_project，因许可证限制强制改为 upstream_pr"

    result = {"repo": full, "license_policy": policy, "proposals": proposals}
    (d / "proposals.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (d / "proposals.md").write_text(render_md(result), encoding="utf-8")
    con = db.connect()
    with con:
        db.set_status(con, full, "proposed")
    con.close()
    return result


def render_md(result):
    lines = ["# 优化提案：" + result["repo"], ""]
    lines.append("**许可证**: " + result["license_policy"]["spdx"])
    for n in result["license_policy"]["notes"]:
        lines.append("> " + n)
    lines.append("")
    for i, p in enumerate(result["proposals"], 1):
        lines.append("## {}. {}".format(i, p.get("title", "")))
        lines.append(
            "- 策略: {} | 类型: {} | 影响: {}/5 | 工作量: {}".format(
                p.get("strategy"), p.get("type"), p.get("impact"), p.get("effort")
            )
        )
        lines.append("- 理由: " + str(p.get("rationale", "")))
        lines.append("- 证据: " + str(p.get("evidence", "")))
        if p.get("license_note"):
            lines.append("- ⚠️ " + p["license_note"])
        ac = p.get("acceptance_criteria") or []
        if ac:
            lines.append("- 验收标准:")
            lines.extend("  - " + str(c) for c in ac)
        lines.append("")
    return "\n".join(lines)
