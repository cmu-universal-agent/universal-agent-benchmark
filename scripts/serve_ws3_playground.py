#!/usr/bin/env python3
"""Serve the local WS3 retail playground without persisting live runs."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
sys.path.insert(0, str(ROOT))

from adapter.task_loader import load_task  # noqa: E402
from scripts.generate_dashboard import build  # noqa: E402

PUBLIC_CASE = ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
MAX_BODY_BYTES = 16_384
MAX_PROMPT_CHARS = 4_000
RUNNERS = {
    "langgraph": (
        "LangGraph",
        "frameworks.langgraph_agent.retail_run",
    ),
    "openai_agents_sdk": (
        "OpenAI Agents SDK",
        "frameworks.openai_agents_sdk.retail_run",
    ),
}


class RequestError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _validated_request(data: Any) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise RequestError(400, "Request body must be a JSON object.")
    framework = data.get("framework")
    prompt = data.get("prompt")
    if framework not in RUNNERS:
        raise RequestError(400, "Choose an available framework.")
    if not isinstance(prompt, str) or not prompt.strip():
        raise RequestError(400, "Customer request cannot be empty.")
    prompt = prompt.strip()
    if len(prompt) > MAX_PROMPT_CHARS:
        raise RequestError(
            400,
            f"Customer request exceeds {MAX_PROMPT_CHARS} characters.",
        )
    return framework, prompt


def _sanitized_trace(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public = []
    for index, call in enumerate(tool_calls):
        error = call.get("error")
        error_type = error.get("error_type") if isinstance(error, dict) else None
        outcome = call.get("outcome")
        if outcome == "success":
            outcome = "ok"
        elif error_type:
            outcome = error_type
        before = call.get("state_before_sha256")
        after = call.get("state_after_sha256")
        state_changed = (
            call.get("state_changed")
            if isinstance(call.get("state_changed"), bool)
            else bool(before and after and before != after)
        )
        public.append(
            {
                "index": index,
                "tool_name": str(call.get("tool_name", "unknown_tool")),
                "outcome": str(outcome or "unknown"),
                "state_changed": state_changed,
            }
        )
    return public


def run_live(framework: str, prompt: str) -> dict[str, Any]:
    framework, prompt = _validated_request(
        {"framework": framework, "prompt": prompt}
    )
    if not os.getenv("OPENAI_API_KEY"):
        raise RequestError(503, "OPENAI_API_KEY is not configured.")
    label, module_name = RUNNERS[framework]
    try:
        runner = importlib.import_module(module_name)
    except ImportError as exc:
        raise RequestError(
            503,
            f"{label} dependencies are not installed in this environment.",
        ) from exc

    task = replace(load_task(PUBLIC_CASE), prompt=prompt)
    result = runner.run_retail_task(task, seed=42)
    return {
        "framework": framework,
        "framework_label": label,
        "case_id": task.case_id,
        "success": result.success,
        "answer": result.final_output or None,
        "error": result.error,
        "latency_seconds": round(result.latency_seconds, 2),
        "trace": _sanitized_trace(result.tool_calls),
        "token_usage": result.token_usage,
        "scope": "local live run; not a benchmark score",
    }


class PlaygroundHandler(BaseHTTPRequestHandler):
    page = b""

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict[str, Any]) -> None:
        self._send(
            status,
            json.dumps(data).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, self.page, "text/html; charset=utf-8")
        elif self.path == "/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/run":
            self._json(404, {"error": "Not found."})
            return
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise RequestError(400, "Invalid request size.") from exc
            if length <= 0 or length > MAX_BODY_BYTES:
                raise RequestError(400, "Invalid request size.")
            data = json.loads(self.rfile.read(length))
            framework, prompt = _validated_request(data)
            self._json(200, run_live(framework, prompt))
        except RequestError as exc:
            self._json(exc.status, {"error": str(exc)})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "Request body must be valid JSON."})
        except Exception as exc:
            print(f"live run failed: {type(exc).__name__}", file=sys.stderr)
            self._json(500, {"error": "Live run failed. Check the server console."})

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(port: int = 8765) -> HTTPServer:
    PlaygroundHandler.page = build(
        "retail",
        include_synthetic_walkthrough=True,
    ).encode("utf-8")
    return HTTPServer(("127.0.0.1", port), PlaygroundHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f"WS3 playground: http://127.0.0.1:{server.server_port}")
    print("Live runs stay local and are not written to results/metrics.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
