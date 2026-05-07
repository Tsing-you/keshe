"""Standalone verifier for the help-model endpoint.

This script tests the SiliconFlow chat-completions endpoint directly and prints
clear diagnostics for network, authentication, model-name, and timeout issues.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

from config import Config


DEFAULT_PROMPT = "请用一句话说明你是否可用，并回答当前系统是否支持普通用户下单。"


def build_payload(model: str, question: str) -> bytes:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 JLU FOODLAB 本地配送系统的帮助助手。"
                    "请简洁、准确地回答关于注册、登录、下单、接单、商家管理、接口和开发环境的问题。"
                ),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
        "top_p": 0.85,
        "max_tokens": 256,
        "stream": False,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def call_model(base_url: str, api_key: str, model: str, question: str, timeout: int) -> tuple[dict, float]:
    request_obj = urllib.request.Request(
        base_url,
        data=build_payload(model, question),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(request_obj, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="ignore")
    elapsed = time.perf_counter() - start
    return json.loads(body), elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify SiliconFlow GLM availability for the help assistant")
    parser.add_argument("--base-url", default=os.getenv("AI_BASE_URL", Config.AI_BASE_URL), help="Chat completions endpoint")
    parser.add_argument("--api-key", default=os.getenv("AI_API_KEY", Config.AI_API_KEY), help="SiliconFlow API key")
    parser.add_argument("--model", default=os.getenv("AI_MODEL", Config.AI_MODEL), help="Model name")
    parser.add_argument("--question", default=DEFAULT_PROMPT, help="Test question")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("AI_VERIFY_TIMEOUT", "30")), help="Request timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        print("[error] AI_API_KEY 为空，无法验证模型。", file=sys.stderr)
        return 2

    print("[info] base_url:", args.base_url)
    print("[info] model:", args.model)
    print("[info] timeout(s):", args.timeout)

    try:
        response_data, elapsed = call_model(args.base_url, args.api_key, args.model, args.question, args.timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        print(f"[error] HTTP {exc.code}: {detail[:800]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"[error] network: {exc.reason}", file=sys.stderr)
        return 1
    except TimeoutError:
        print(f"[error] timeout: request exceeded {args.timeout}s", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("[error] response is not valid JSON", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[error] unexpected: {exc}", file=sys.stderr)
        return 1

    print(f"[ok] response_time_s: {elapsed:.2f}")

    choices = response_data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if content:
            print("[ok] model_answer:")
            print(content)
            return 0

    error = response_data.get("error", {})
    if isinstance(error, dict) and error.get("message"):
        print(f"[error] api_error: {error['message']}", file=sys.stderr)
    else:
        print("[error] no usable answer returned by the model", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())