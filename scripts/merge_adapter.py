"""Merge the LoRA adapter into the base model -> one standalone fp16 model (no retraining).

  python scripts/merge_adapter.py                      # outputs/qwen3-4b-triage-lora -> outputs/qwen3-4b-triage-merged
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
BASE_FP16 = "Qwen/Qwen3-4B-Instruct-2507"  # the original (unquantised) weights the 4-bit base was made from


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_FP16)
    ap.add_argument("--adapter", default=str(ROOT / "outputs/qwen3-4b-triage-lora"))
    ap.add_argument("--out", default=str(ROOT / "outputs/qwen3-4b-triage-merged"))
    a = ap.parse_args()

    model = AutoModelForCausalLM.from_pretrained(a.base, torch_dtype=torch.float16, device_map="cpu")
    model = PeftModel.from_pretrained(model, a.adapter)
    model = model.merge_and_unload()
    model.save_pretrained(a.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(a.adapter).save_pretrained(a.out)
    print(f"merged model saved to {a.out}")


if __name__ == "__main__":
    main()
