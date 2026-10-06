"""QLoRA fine-tune of Qwen3-4B-Instruct-2507 on the triage data with Unsloth + TRL.

Run on a GPU (Colab T4 is enough):
  python scripts/train.py                       # defaults below
  python scripts/train.py --epochs 3 --wandb    # log to Weights & Biases (needs WANDB_API_KEY / wandb login)

Loss is computed on the assistant (JSON) tokens only. Saves the LoRA adapter to outputs/<run-name>/.
"""
from __future__ import annotations

# Unsloth must be imported before transformers/trl/peft.
from unsloth import FastLanguageModel  # isort: skip
from unsloth.chat_templates import train_on_responses_only  # isort: skip

import argparse
import json
from pathlib import Path

from datasets import Dataset
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).resolve().parent.parent
BASE = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"


def load(split: str) -> list[dict]:
    p = ROOT / "data/processed" / f"{split}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--run-name", default="qwen3-4b-triage-lora")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--max-seq-len", type=int, default=1024)
    ap.add_argument("--train-limit", type=int, default=0, help="use only N training rows (learning-curve runs)")
    ap.add_argument("--eval-steps", type=int, default=50, help="validation (and checkpoint) interval in steps")
    ap.add_argument("--wandb", action="store_true")
    ap.add_argument("--seed", type=int, default=3407)
    a = ap.parse_args()

    model, tok = FastLanguageModel.from_pretrained(
        model_name=a.base, max_seq_length=a.max_seq_len, load_in_4bit=True, dtype=None)  # dtype auto: fp16 on T4
    model = FastLanguageModel.get_peft_model(
        model, r=a.rank, lora_alpha=a.rank, lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=a.seed)

    def to_text(rows: list[dict]) -> Dataset:
        return Dataset.from_list([{"text": tok.apply_chat_template(r["messages"], tokenize=False,
                                                                   add_generation_prompt=False)} for r in rows])

    train_rows = load("train")
    if a.train_limit:
        train_rows = train_rows[:a.train_limit]
    train_ds, val_ds = to_text(train_rows), to_text(load("val"))
    print(f"train {len(train_ds)}  val {len(val_ds)}\n--- sample ---\n{train_ds[0]['text'][-400:]}")

    out_dir = ROOT / "outputs" / a.run_name
    trainer = SFTTrainer(
        model=model, tokenizer=tok, train_dataset=train_ds, eval_dataset=val_ds,
        args=SFTConfig(
            dataset_text_field="text", max_seq_length=a.max_seq_len, dataset_num_proc=2, packing=False,
            per_device_train_batch_size=a.batch_size, per_device_eval_batch_size=a.batch_size,
            gradient_accumulation_steps=a.grad_accum, num_train_epochs=a.epochs, learning_rate=a.lr,
            lr_scheduler_type="cosine", warmup_ratio=0.05, weight_decay=0.01, optim="adamw_8bit",
            fp16=True, bf16=False,  # T4 has no bf16; switch if you rent an A100/L4
            logging_steps=10, eval_strategy="steps", eval_steps=a.eval_steps, save_strategy="steps", save_steps=a.eval_steps,
            save_total_limit=2, seed=a.seed, output_dir=str(out_dir / "checkpoints"),
            report_to="wandb" if a.wandb else "none", run_name=a.run_name),
    )
    # compute loss only on the assistant turn (the JSON), not on the system prompt / ticket
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                      response_part="<|im_start|>assistant\n")
    stats = trainer.train()
    print(stats.metrics)
    print("final eval:", trainer.evaluate())

    model.save_pretrained(str(out_dir))   # LoRA adapter only (~100 MB)
    tok.save_pretrained(str(out_dir))
    print(f"saved adapter to {out_dir}")


if __name__ == "__main__":
    main()
