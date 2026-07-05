import json
import re

import anthropic

from . import config


class LLMError(RuntimeError):
    pass


_client = None


def client():
    global _client
    if _client is None:
        try:
            # 无参构造：自动读取 ANTHROPIC_API_KEY（config 已加载 .env）或 ant auth 本地凭证
            _client = anthropic.Anthropic()
        except TypeError as e:
            raise LLMError(
                "未找到 Anthropic 凭证：在 oss-scout/.env 配置 ANTHROPIC_API_KEY，"
                "或先运行 `ant auth login`"
            ) from e
    return _client


def ask(system, user, max_tokens=8000, model=None):
    try:
        resp = client().messages.create(
            model=model or config.MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        raise LLMError(
            "Anthropic API 认证失败：检查 oss-scout/.env 里的 ANTHROPIC_API_KEY"
        )
    except anthropic.RateLimitError:
        raise LLMError("Anthropic API 限流，稍后重试")
    except anthropic.APIStatusError as e:
        raise LLMError("Anthropic API 错误 {}: {}".format(e.status_code, e.message))
    except anthropic.APIConnectionError:
        raise LLMError("无法连接 Anthropic API，检查网络")
    return "".join(b.text for b in resp.content if b.type == "text")


def ask_json(system, user, max_tokens=8000, model=None):
    text = ask(
        system,
        user + "\n\n只输出一个 JSON 对象，用 ```json 代码块包裹，不要输出其他文字。",
        max_tokens,
        model,
    )
    m = re.search(r"```json\s*(.+?)```", text, re.S)
    raw = m.group(1) if m else text
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(
            "模型输出无法解析为 JSON（{}）。原始输出前 500 字：\n{}".format(e, text[:500])
        )
