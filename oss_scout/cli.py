import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import analyze as analyze_mod
from . import brief as brief_mod
from . import config, db
from . import discover as discover_mod
from . import drafts as drafts_mod
from . import propose as propose_mod
from .github_api import GitHubError
from .llm import LLMError

console = Console()


def _print_candidates(items, title, show_status=False):
    t = Table(title=title)
    t.add_column("#", justify="right")
    t.add_column("仓库", style="bold")
    t.add_column("⭐总数", justify="right")
    t.add_column("⭐近期", justify="right")
    t.add_column("语言")
    if show_status:
        t.add_column("状态")
    t.add_column("简介", max_width=46, overflow="ellipsis")
    for i, it in enumerate(items, 1):
        row = [
            str(i),
            it.get("repo", ""),
            "{:,}".format(it.get("stars") or 0),
            "{:,}".format(it.get("stars_recent") or 0),
            it.get("language") or "",
        ]
        if show_status:
            row.append(it.get("status") or "new")
        row.append(it.get("description") or "")
        t.add_row(*row)
    console.print(t)


def cmd_discover(args):
    items = discover_mod.discover(args.language, args.since)
    if not items:
        console.print("[yellow]没有发现候选仓库[/yellow]")
        return
    src = items[0]["source"]
    _print_candidates(items, "发现 {} 个候选（来源: {}）".format(len(items), src))
    console.print("下一步: [bold]oss-scout analyze <owner/repo>[/bold]")


def cmd_list(args):
    con = db.connect()
    rows = [dict(r) for r in db.list_candidates(con, args.limit)]
    con.close()
    if not rows:
        console.print("[yellow]候选池为空，先运行 oss-scout discover[/yellow]")
        return
    _print_candidates(rows, "候选池（按近期 star 排序）", show_status=True)


def cmd_analyze(args):
    console.print("抓取 {} 的 README / issues / 文件结构 …".format(args.repo))
    meta, report = analyze_mod.analyze(args.repo)
    console.print(Markdown(report))
    console.print(
        "\n[green]✓[/green] 报告已存: {}".format(config.report_dir(args.repo) / "assessment.md")
    )
    console.print("下一步: [bold]oss-scout propose {}[/bold]".format(args.repo))


def cmd_propose(args):
    result = propose_mod.propose(args.repo)
    d = config.report_dir(args.repo)
    console.print(Markdown((d / "proposals.md").read_text(encoding="utf-8")))
    console.print("\n[green]✓[/green] 提案已存: {}".format(d / "proposals.md"))
    console.print(
        "下一步: [bold]oss-scout brief {} --proposal N[/bold]".format(args.repo)
    )


def cmd_brief(args):
    path = brief_mod.build_brief(args.repo, args.proposal)
    console.print(Markdown(path.read_text(encoding="utf-8")))
    console.print("\n[green]✓[/green] 简报已存: {}".format(path))


def cmd_draft(args):
    path = drafts_mod.draft(args.repo, args.proposal)
    console.print(Markdown(path.read_text(encoding="utf-8")))
    console.print("\n[green]✓[/green] 草稿已存: {}（人工审核后手动发布）".format(path))


def cmd_run(args):
    items = discover_mod.discover(args.language, args.since)
    if not items:
        console.print("[yellow]没有发现候选仓库[/yellow]")
        return
    _print_candidates(items[: args.top], "本轮处理前 {} 个候选".format(args.top))
    for it in items[: args.top]:
        repo = it["repo"]
        console.rule("[bold]{}[/bold]".format(repo))
        try:
            analyze_mod.analyze(repo)
            result = propose_mod.propose(repo)
        except (GitHubError, LLMError) as e:
            console.print("[red]跳过 {}: {}[/red]".format(repo, e))
            continue
        for i, p in enumerate(result["proposals"], 1):
            console.print(
                "  {}. [{}] {} （影响 {}/5，工作量 {}）".format(
                    i, p.get("strategy"), p.get("title"), p.get("impact"), p.get("effort")
                )
            )
        console.print("  报告目录: {}".format(config.report_dir(repo)))
    console.print(
        "\n挑一个提案继续: [bold]oss-scout brief <owner/repo> --proposal N[/bold]"
    )


def main():
    parser = argparse.ArgumentParser(
        prog="oss-scout",
        description="发现 GitHub trending → 理解需求 → 生成优化提案与实施简报（贡献优先，发布前人工把关）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover", help="抓取 GitHub trending（失败自动回退 search API）")
    p.add_argument("--language", "-l", default=None, help="如 python / rust / typescript")
    p.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("list", help="查看候选池与各仓库处理状态")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("analyze", help="深入分析一个仓库（README/issues/结构 → 需求评估）")
    p.add_argument("repo", help="owner/repo")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("propose", help="生成优化提案（含许可证与贡献策略把关）")
    p.add_argument("repo", help="owner/repo")
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("brief", help="为选定提案生成实施简报（交给 Claude Code 执行）")
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--proposal", "-p", type=int, default=1)
    p.set_defaults(func=cmd_brief)

    p = sub.add_parser("draft", help="生成 PR 描述 + X 帖子草稿（人工审核后手动发布）")
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--proposal", "-p", type=int, default=1)
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("run", help="端到端：discover → 逐个 analyze + propose")
    p.add_argument("--language", "-l", default=None)
    p.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily")
    p.add_argument("--top", type=int, default=3)
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    try:
        args.func(args)
    except (GitHubError, LLMError, RuntimeError) as e:
        console.print("[red]错误：{}[/red]".format(e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
