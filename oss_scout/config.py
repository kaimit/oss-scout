import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# override=True：项目 .env 优先于 shell 环境变量，避免外部残留的坏 key 压住配置
load_dotenv(PROJECT_ROOT / ".env", override=True)

DATA_DIR = Path(os.getenv("OSS_SCOUT_HOME", str(PROJECT_ROOT))) / "data"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "oss_scout.db"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or None
MODEL = os.getenv("OSS_SCOUT_MODEL", "claude-opus-4-8")


def ensure_dirs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def report_dir(full_name):
    d = REPORTS_DIR / full_name.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    return d
