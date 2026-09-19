"""
Fine-tune DeBERTa on a JSON list with ``claim`` and ``label`` (0 or 1).

From ``ai-modelling/``:

  python src/training/train_deberta.py --train data/train.json --output-dir checkpoints/misinfo-deberta
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from tqdm.auto import tqdm
from transformers import get_linear_schedule_with_warmup

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.misinformation.deberta import (
    DebertaMisinfoTrainConfig,
    TextClsDataset,
    build_fresh_classifier,
    collate_text_cls_batch,
    load_table,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


@torch.no_grad()
def evaluate_classification(model: Any, loader: Any, device: torch.device) -> dict[str, float]:
    model.eval()
    ys: list[int] = []
    preds: list[int] = []
    for batch in loader:
        labels = batch["labels"].tolist()
        batch = {k: v.to(device) for k, v in batch.items()}
        logits = model(**batch).logits
        pred = torch.argmax(logits, dim=-1).tolist()
        ys.extend(labels)
        preds.extend(pred)
    y = np.asarray(ys, dtype=int)
    p = np.asarray(preds, dtype=int)
    acc = float(accuracy_score(y, p))
    prf = precision_recall_fscore_support(y, p, average="binary", pos_label=1, zero_division=0)
    macro = precision_recall_fscore_support(y, p, average="macro", zero_division=0)
    return {
        "accuracy": acc,
        "f1_binary_pos1": float(prf[2]),
        "precision_binary_pos1": float(prf[0]),
        "recall_binary_pos1": float(prf[1]),
        "macro_f1": float(macro[2]),
    }

OUTPUT_DIR = "src/models/misinformation/checkpoints/misinfo-deberta"
TRAIN_DIR = "src/data/misinformation/kaggle1_5k.json"

def main() -> None:
    ap = argparse.ArgumentParser(description="Fine-tune DeBERTa for binary misinformation (claim + label JSON).")
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--val", type=Path, default=None)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--hf-model-id", type=str, default=DebertaMisinfoTrainConfig.hf_model_id)
    ap.add_argument("--test-size", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-len", type=int, default=DebertaMisinfoTrainConfig.max_len)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup-ratio", type=float, default=0.06)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--early-stopping-patience", type=int, default=2)
    ap.add_argument("--min-delta", type=float, default=1e-4)
    ap.add_argument("--num-workers", type=int, default=0)
    ap.add_argument("--gradient-checkpointing", action="store_true")
    # LoRA: parameter-efficient fine-tuning. When --lora is set we freeze the base
    # DeBERTa and train only low-rank adapters (+ the classifier head).
    ap.add_argument("--lora", action="store_true", help="Use LoRA instead of full fine-tuning.")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument(
        "--lora-save-adapter",
        action="store_true",
        help="Save only the LoRA adapter (small). Default merges it into the base "
        "so the checkpoint loads like any full DeBERTa checkpoint.",
    )
    args = ap.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_df = load_table(args.train, "claim", "label")
    if args.val is not None:
        val_df = load_table(args.val, "claim", "label")
    else:
        train_df, val_df = train_test_split(
            train_df,
            test_size=args.test_size,
            random_state=args.seed,
            stratify=train_df["label"],
        )

    tokenizer, model = build_fresh_classifier(args.hf_model_id)
    if args.lora:
        # deberta-v3 (v2 arch) attention exposes separate query/key/value_proj Linears.
        from peft import LoraConfig, TaskType, get_peft_model

        lora_cfg = LoraConfig(
            task_type=TaskType.SEQ_CLS,  # keeps the classifier head trainable
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=["query_proj", "key_proj", "value_proj"],
            bias="none",
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()
    model.to(device)
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    train_ds = TextClsDataset(train_df["text"].tolist(), train_df["label"].tolist(), tokenizer, args.max_len)
    val_ds = TextClsDataset(val_df["text"].tolist(), val_df["label"].tolist(), tokenizer, args.max_len)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_text_cls_batch,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate_text_cls_batch,
        pin_memory=device.type == "cuda",
    )

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    total_steps = int(np.ceil(len(train_loader) / args.grad_accum)) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    sched = get_linear_schedule_with_warmup(
        optim, num_warmup_steps=warmup_steps, num_training_steps=max(1, total_steps)
    )

    use_amp = device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    best_f1 = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    patience = 0

    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        optim.zero_grad(set_to_none=True)
        pbar = tqdm(train_loader, desc=f"train epoch {epoch + 1}/{args.epochs}")
        for step, batch in enumerate(pbar, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.cuda.amp.autocast(enabled=use_amp):
                out = model(**batch)
                loss = out.loss / args.grad_accum
            scaler.scale(loss).backward()
            running_loss += float(loss.detach().item()) * args.grad_accum

            if step % args.grad_accum == 0:
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                scaler.step(optim)
                scaler.update()
                optim.zero_grad(set_to_none=True)
                sched.step()

            pbar.set_postfix(loss=f"{running_loss / step:.4f}")

        if len(train_loader) % args.grad_accum != 0:
            scaler.unscale_(optim)
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            scaler.step(optim)
            scaler.update()
            optim.zero_grad(set_to_none=True)

        metrics = evaluate_classification(model, val_loader, device)
        print(
            f"epoch {epoch + 1}: val_acc={metrics['accuracy']:.4f} "
            f"val_macro_f1={metrics['macro_f1']:.4f} val_f1_pos1={metrics['f1_binary_pos1']:.4f}"
        )

        if metrics["macro_f1"] > best_f1 + args.min_delta:
            best_f1 = metrics["macro_f1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        if patience >= args.early_stopping_patience:
            print("early stopping")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.lora and not args.lora_save_adapter:
        # Fold adapters into the base weights so the checkpoint loads like a normal
        # full DeBERTa checkpoint (no PEFT needed at inference time).
        model = model.merge_and_unload()
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    meta = {
        "hf_model_id": args.hf_model_id,
        "max_len": args.max_len,
        "best_val_macro_f1": best_f1,
        "n_train": int(len(train_df)),
        "n_val": int(len(val_df)),
        "text_field_train": "claim",
        "label_field_train": "label",
    }
    (args.output_dir / "training_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"saved model to {args.output_dir}")


if __name__ == "__main__":
    main()