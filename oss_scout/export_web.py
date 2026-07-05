import json
from datetime import datetime, timezone

from . import config


def export_web(out_path=None):
    """把 data/reports/ 下已生成的分析+提案导出成 web/data/reports.json。"""
    config.ensure_dirs()
    reports = {}
    if config.REPORTS_DIR.exists():
        for d in sorted(config.REPORTS_DIR.iterdir()):
            prop = d / "proposals.json"
            if not d.is_dir() or not prop.exists():
                continue
            pdata = json.loads(prop.read_text(encoding="utf-8"))
            repo = pdata.get("repo") or d.name.replace("__", "/")
            meta_path = d / "meta.json"
            assess_path = d / "assessment.md"
            reports[repo] = {
                "meta": json.loads(meta_path.read_text(encoding="utf-8"))
                if meta_path.exists() else {},
                "license_policy": pdata.get("license_policy", {}),
                "proposals": pdata.get("proposals", []),
                "assessment_excerpt": assess_path.read_text(encoding="utf-8")[:1200]
                if assess_path.exists() else "",
            }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reports": reports,
    }
    if out_path is None:
        out_path = config.PROJECT_ROOT / "web" / "data" / "reports.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path, len(reports)
