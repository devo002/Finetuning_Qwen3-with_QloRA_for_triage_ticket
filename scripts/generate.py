"""Synthetic ticket generation via the Claude Batch API (Haiku 4.5).

  python scripts/generate.py plan    --run pilot --n 100 --seed 1   # no API call; writes specs, prints a sample prompt
  python scripts/generate.py submit  --run pilot                    # sends the batch (needs ANTHROPIC_API_KEY)
  python scripts/generate.py status  --run pilot
  python scripts/generate.py collect --run pilot                    # writes data/generated/<run>/tickets.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from triage.scenarios import sample_specs  # noqa: E402

MODEL = "claude-haiku-4-5"
TICKETS_PER_REQUEST = 5
LANG_NAME = {"de": "German", "en": "English"}

SYSTEM = (
    "You write realistic synthetic customer-support tickets for a German residential solar and "
    "heat-pump company called Empire. The tickets are training data, so they must look like real, "
    "messy messages from real customers. Follow each spec exactly, including what must NOT be "
    "mentioned. Never mention that the text is synthetic."
)


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def spec_to_text(i: int, s: dict) -> str:
    g = s["gen"]
    lang = LANG_NAME[g["language"]]
    other = LANG_NAME["en" if g["language"] == "de" else "de"]
    lines = [f"Ticket {i}:"]
    lines.append(f"- Channel: {g['channel']} (customer region: {g['region']})")
    lines.append(f"- Main language: {lang}"
                 + (f", with a few {other} words or phrases mixed in" if g["mixed"] else ", no mixing"))
    lines.append(f"- Writing style: {'; '.join(g['styles'])}")
    if "topic" in g:  # purely administrative
        lines.append(f"- Content: an administrative message where {g['topic']}. No technical fault is reported.")
    else:
        lines.append(f"- Equipment: {g['equipment']}")
        lines.append(f"- What the customer experiences: {g['situation']}")
        if g.get("admin_wrapper"):
            lines.append(f"- The message is mainly about an administrative matter ({g['admin_wrapper']}), "
                         "but the customer also mentions the problem above, maybe briefly or in passing.")
    if g.get("code"):
        lines.append(f"- The text MUST contain the error code exactly as written: {g['code']}")
    else:
        lines.append("- Do NOT mention any error code or code number.")
    if g.get("brand"):
        eq = f" (the customer owns their {g['equipment']})" if "topic" in g and g.get("equipment") else ""
        lines.append(f"- The text MUST name the manufacturer: {g['brand']}{eq}")
    else:
        lines.append("- Do NOT name any manufacturer or brand (say 'inverter', 'heat pump', etc.).")
    return "\n".join(lines)


def build_prompt(specs: list[dict]) -> str:
    body = "\n\n".join(spec_to_text(i + 1, s) for i, s in enumerate(specs))
    return (
        f"Write {len(specs)} tickets, one per spec below, in the same order.\n"
        "A phone-transcript ticket has a short generic subject like 'Phone call' or an empty subject.\n"
        "Do not state severity or categories. Do not add the customer's name.\n"
        'Return ONLY a JSON array of exactly '
        f'{len(specs)} objects, each {{"subject": string, "body": string}}. No markdown, no commentary.\n\n'
        + body
    )


def run_dir(run: str) -> Path:
    d = ROOT / "data" / "generated" / run
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_plan(a) -> None:
    specs = [asdict(s) for s in sample_specs(a.n, a.seed)]
    d = run_dir(a.run)
    (d / "specs.jsonl").write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in specs) + "\n",
                                   encoding="utf-8")
    groups = [specs[i:i + TICKETS_PER_REQUEST] for i in range(0, len(specs), TICKETS_PER_REQUEST)]
    print(f"{len(specs)} specs -> {len(groups)} requests of <= {TICKETS_PER_REQUEST} tickets. Saved {d/'specs.jsonl'}")
    from collections import Counter
    print("scenario mix:", dict(Counter(s['scenario'].split('_')[0] for s in specs)))
    print("intent mix:  ", dict(Counter(s['label']['intent'] for s in specs)))
    print("severity mix:", dict(Counter(s['label']['severity'] for s in specs)))
    print("\n----- sample prompt (request 1) -----\n" + build_prompt(groups[0]))


def cmd_submit(a) -> None:
    load_env()
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    d = run_dir(a.run)
    if (d / "batch.json").exists() and not a.force:
        sys.exit("batch.json exists - already submitted. Use --force to submit again (costs money).")
    specs = read_jsonl(d / "specs.jsonl")
    groups = [specs[i:i + TICKETS_PER_REQUEST] for i in range(0, len(specs), TICKETS_PER_REQUEST)]
    reqs = [
        Request(custom_id=f"req-{n:04d}", params=MessageCreateParamsNonStreaming(
            model=MODEL, max_tokens=4000, system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(g)}]))
        for n, g in enumerate(groups)
    ]
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=reqs)
    (d / "batch.json").write_text(json.dumps({"id": batch.id, "n_requests": len(reqs), "model": MODEL}), encoding="utf-8")
    print(f"Submitted batch {batch.id} ({len(reqs)} requests). Check with: status --run {a.run}")


def cmd_status(a) -> None:
    load_env()
    import anthropic
    info = json.loads((run_dir(a.run) / "batch.json").read_text(encoding="utf-8"))
    b = anthropic.Anthropic().messages.batches.retrieve(info["id"])
    print(b.processing_status, b.request_counts)


def parse_tickets(text: str, k: int) -> list[dict] | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        arr = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not (isinstance(arr, list) and len(arr) == k):
        return None
    if not all(isinstance(t, dict) and isinstance(t.get("subject"), str) and isinstance(t.get("body"), str)
               for t in arr):
        return None
    return arr


def cmd_collect(a) -> None:
    load_env()
    import anthropic
    d = run_dir(a.run)
    info = json.loads((d / "batch.json").read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    b = client.messages.batches.retrieve(info["id"])
    if b.processing_status != "ended":
        sys.exit(f"Batch not finished yet: {b.processing_status} {b.request_counts}")
    specs = read_jsonl(d / "specs.jsonl")
    groups = {f"req-{n:04d}": specs[i:i + TICKETS_PER_REQUEST]
              for n, i in enumerate(range(0, len(specs), TICKETS_PER_REQUEST))}
    out, failed, in_tok, out_tok = [], [], 0, 0
    for r in client.messages.batches.results(info["id"]):
        g = groups[r.custom_id]
        if r.result.type != "succeeded":
            failed.append((r.custom_id, r.result.type))
            continue
        msg = r.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        text = next((c.text for c in msg.content if c.type == "text"), "")
        tickets = parse_tickets(text, len(g))
        if tickets is None:
            failed.append((r.custom_id, "unparseable"))
            continue
        for s, t in zip(g, tickets):
            out.append({"id": s["id"], "ticket": {"channel": s["gen"]["channel"], "subject": t["subject"].strip(),
                                                   "body": t["body"].strip()},
                        "label": s["label"], "meta": {"scenario": s["scenario"], "hard": s["hard"],
                                                       "region": s["gen"]["region"]}})
    out.sort(key=lambda x: x["id"])
    (d / "tickets.jsonl").write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    cost = (in_tok * 1.0 + out_tok * 5.0) / 1e6 * 0.5  # Haiku 4.5, batch = 50% of $1/$5 per 1M
    print(f"Wrote {len(out)} tickets. Failed requests: {failed or 'none'}")
    print(f"Tokens in/out: {in_tok}/{out_tok}  ~cost ${cost:.3f} (batch pricing)")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("plan", cmd_plan), ("submit", cmd_submit), ("status", cmd_status), ("collect", cmd_collect)]:
        sp = sub.add_parser(name)
        sp.add_argument("--run", default="pilot")
        if name == "plan":
            sp.add_argument("--n", type=int, default=100)
            sp.add_argument("--seed", type=int, default=1)
        if name == "submit":
            sp.add_argument("--force", action="store_true")
        sp.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
