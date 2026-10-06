"""Benchmark Smart Dispatcher's CURRENT triage call (production baseline) on our test sets.

Reads the system prompt and tool schema straight out of Mcp/src/empire_dispatcher/graph/nodes.py
(via ast, so no chromadb / langgraph install is needed) and calls Claude exactly as triage_node does:
  forced tool call, max_tokens=500, user message "Customer/Region/Subject/Body".
Bypasses the semantic triage cache and LangSmith, so latency and cost are honest per-call numbers.

  python scripts/baseline_dispatcher.py --splits test real_test [--limit 20]

Writes outputs/preds_dispatcher-prod_<split>.jsonl in the same format as evaluate.py.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate import read_jsonl  # noqa: E402
from generate import load_env  # noqa: E402

REPO = ROOT / "Mcp"
PRICES = {"claude-sonnet-4-6": (3.0, 15.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-4-5": (1.0, 5.0)}


def load_production_prompt() -> tuple[str, dict]:
    tree = ast.parse((REPO / "src/empire_dispatcher/graph/nodes.py").read_text(encoding="utf-8"))
    env: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ("_TRIAGE_SYSTEM", "_KNOWN_MANUFACTURERS", "_TRIAGE_TOOL"):
            env[node.targets[0].id] = eval(compile(ast.Expression(node.value), "nodes.py", "eval"), {}, env)  # noqa: S307
    return env["_TRIAGE_SYSTEM"], env["_TRIAGE_TOOL"]


def configured_model() -> str:
    m = re.search(r"^CLAUDE_MODEL=(\S+)", (REPO / ".env").read_text(encoding="utf-8"), re.M) if (REPO / ".env").exists() else None
    return m.group(1) if m else "claude-sonnet-4-6"  # config.py default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["test", "real_test"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default=None, help="override CLAUDE_MODEL from Mcp/.env")
    a = ap.parse_args()

    import anthropic
    load_env()
    client = anthropic.Anthropic()
    system, tool = load_production_prompt()
    model = a.model or configured_model()
    pin, pout = PRICES[model]
    print(f"production baseline: model={model}")

    def one(r: dict) -> dict:
        user = r["messages"][1]["content"]  # "Channel: ..\nSubject: ..\nBody: .."
        subject = re.search(r"^Subject: (.*)$", user, re.M).group(1)
        body = user.split("\nBody: ", 1)[1]
        ticket = f"Customer: ?\nRegion: ?\nSubject: {subject}\nBody: {body}\n"  # name/region unknown in our data
        t0 = time.perf_counter()
        msg = client.messages.create(model=model, max_tokens=500, system=system,
                                     messages=[{"role": "user", "content": ticket}],
                                     tools=[tool], tool_choice={"type": "tool", "name": tool["name"]})
        dt = time.perf_counter() - t0
        tu = next((b for b in msg.content if b.type == "tool_use"), None)
        d = tu.input if tu else {}
        triage = {  # same post-processing/defaults as triage_node
            "error_code": d.get("error_code"), "manufacturer": d.get("manufacturer"),
            "severity": d.get("severity") or "medium", "intent": d.get("intent") or "general",
            "required_skills": d.get("required_skills") or [], "detected_language": d.get("detected_language") or "de"}
        u = msg.usage
        return {"id": r["id"], "raw": json.dumps(triage, ensure_ascii=False), "latency_s": dt,
                "in_tokens": u.input_tokens, "out_tokens": u.output_tokens,
                "cost_usd": (u.input_tokens * pin + u.output_tokens * pout) / 1e6}

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    for split in a.splits:
        rows = read_jsonl(ROOT / "data/processed" / f"{split}.jsonl")
        if a.limit:
            rows = rows[:a.limit]
        print(f"{split}: {len(rows)} tickets")
        t0 = time.perf_counter()
        with ThreadPoolExecutor(a.workers) as ex:
            preds = list(ex.map(one, rows))
        wall = time.perf_counter() - t0
        for p in preds:
            p["wall_s_total"] = wall
        path = out_dir / f"preds_dispatcher-prod_{split}.jsonl"
        path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n", encoding="utf-8")
        print(f"  wrote {path} ({wall:.1f}s, ${sum(p['cost_usd'] for p in preds):.3f})")


if __name__ == "__main__":
    main()
