"""
Train the multi-task DeBERTa (misinformation + urgency + humanitarian).

One shared DeBERTa encoder with three classification heads (see
``notebooks/research/multitask_NLP/urgency_humanitarian_integration.md``). Two
label sources feed it:

  * misinfo_unified.json  -> the ``misinfo`` head only.
  * crisis_unified.json   -> the ``urgency`` AND ``humanitarian`` heads (both
    labels sit on the same crisis example).

A batch contributes the loss of the head(s) it carries labels for. Misinfo uses
cross-entropy (balanced); the imbalanced crisis heads use focal loss with
inverse-frequency class weights.

Build the unified files first:

    python src/data/misinformation/build_unified_data.py

Then, from ``ai-modelling/``:

    python src/training/deberta_multitask_train.py \
        --misinfo src/data/misinformation/unified/misinfo_unified.json \
        --crisis  src/data/misinformation/unified/crisis_unified.json \
        --output-dir src/models/misinformation/checkpoints/multitask-deberta

Add ``--lora`` for parameter-efficient fine-tuning (adapters merged into the
encoder at save time, so the checkpoint reloads with the normal loader).
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
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.misinformation.deberta import (
    DEFAULT_HF_MODEL_ID,
    DEFAULT_TASKS,
    MultiTaskDeberta,
    save_multitask_checkpoint,
)

# Which unified-file field feeds which head.
CRISIS_TASKS = ("urgency", "humanitarian")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# --------------------------------------------------------------------------- #
# Datasets: tokenize on the fly, one item carries the label(s) for its source. #
# --------------------------------------------------------------------------- #
class _EncodedText(Dataset):
    """Base: tokenize a list of strings to padded tensors."""

    def __init__(self, texts: list[str], tokenizer: Any, max_len: int):
        if max_len <= 0:
            raise ValueError("max_len must be greater than zero")
        self.texts = [str(t) for t in texts]
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.texts)

    def _encode(self, idx: int) -> dict[str, torch.Tensor]:
        enc = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in enc.items()}


class MisinfoDataset(_EncodedText):
    def __init__(self, texts, labels, tokenizer, max_len):
        super().__init__(texts, tokenizer, max_len)
        self.labels = [int(x) for x in labels]

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self._encode(idx)
        item["misinfo_labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


class CrisisDataset(_EncodedText):
    def __init__(self, texts, urgency, humanitarian, tokenizer, max_len):
        super().__init__(texts, tokenizer, max_len)
        self.urgency = [int(x) for x in urgency]
        self.humanitarian = [int(x) for x in humanitarian]

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self._encode(idx)
        item["urgency_labels"] = torch.tensor(self.urgency[idx], dtype=torch.long)
        item["humanitarian_labels"] = torch.tensor(self.humanitarian[idx], dtype=torch.long)
        return item


def collate(batch: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
    if not batch:
        raise ValueError("batch must not be empty")
    return {k: torch.stack([b[k] for b in batch], dim=0) for k in batch[0]}


# --------------------------------------------------------------------------- #
# Loss                                                                        #
# --------------------------------------------------------------------------- #
class FocalLoss(nn.Module):
    """gamma>0 down-weights easy examples; ``weight`` adds per-class balancing."""

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight if weight is not None else None)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        logp = F.log_softmax(logits, dim=-1)
        ce = F.nll_loss(logp, target, weight=self.weight, reduction="none")
        pt = logp.gather(1, target.unsqueeze(1)).squeeze(1).exp()
        return ((1.0 - pt) ** self.gamma * ce).mean()


def class_weights(labels: list[int], num_labels: int) -> torch.Tensor:
    """Inverse-frequency weights, normalized to mean 1 (unseen classes -> weight 1)."""
    counts = np.bincount(labels, minlength=num_labels).astype(np.float64)
    inv = np.where(counts > 0, counts.sum() / (num_labels * counts), 1.0)
    inv = inv / inv.mean()
    return torch.tensor(inv, dtype=torch.float32)


# --------------------------------------------------------------------------- #
# Eval                                                                        #
# --------------------------------------------------------------------------- #
@torch.no_grad()
def evaluate_head(model: MultiTaskDeberta, loader: DataLoader, task: str, device) -> dict[str, float]:
    model.eval()
    ys: list[int] = []
    preds: list[int] = []
    for batch in loader:
        labels = batch[f"{task}_labels"].tolist()
        logits = model(
            input_ids=batch["input_ids"].to(device),
            attention_mask=batch["attention_mask"].to(device),
            token_type_ids=batch.get("token_type_ids", torch.zeros_like(batch["input_ids"])).to(device),
            tasks=[task],
        )[task]
        preds.extend(torch.argmax(logits, dim=-1).tolist())
        ys.extend(labels)
    prf = precision_recall_fscore_support(ys, preds, average="macro", zero_division=0)
    return {
        "accuracy": float(accuracy_score(ys, preds)),
        "macro_f1": float(prf[2]),
        "macro_precision": float(prf[0]),
        "macro_recall": float(prf[1]),
        "weighted_f1": float(f1_score(ys, preds, average="weighted", zero_division=0)),
        "n": len(ys),
    }


def batch_loss(model, batch, tasks_present, losses, device) -> torch.Tensor:
    """Sum the loss over the heads this batch carries labels for (encode once)."""
    logits = model(
        input_ids=batch["input_ids"].to(device),
        attention_mask=batch["attention_mask"].to(device),
        token_type_ids=batch.get("token_type_ids", torch.zeros_like(batch["input_ids"])).to(device),
        tasks=list(tasks_present),
    )
    return sum(
        losses[t](logits[t], batch[f"{t}_labels"].to(device)) for t in tasks_present
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Train multi-task DeBERTa (misinfo + urgency + humanitarian).")
    ap.add_argument("--misinfo", type=Path, required=True)
    ap.add_argument("--crisis", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--hf-model-id", type=str, default=DEFAULT_HF_MODEL_ID)
    ap.add_argument("--val-size", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup-ratio", type=float, default=0.06)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--focal-gamma", type=float, default=2.0)
    ap.add_argument("--crisis-oversample", type=int, default=1,
                    help="Repeat crisis batches N times per epoch to up-weight the smaller tasks.")
    ap.add_argument("--early-stopping-patience", type=int, default=2)
    ap.add_argument("--min-delta", type=float, default=1e-4)
    ap.add_argument("--num-workers", type=int, default=0)
    ap.add_argument("--gradient-checkpointing", action="store_true")
    # LoRA (parameter-efficient): adapters on the encoder, merged into it on save.
    ap.add_argument("--lora", action="store_true")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    args = ap.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ---- data ----------------------------------------------------------- #
    misinfo = json.loads(args.misinfo.read_text(encoding="utf-8"))
    crisis = json.loads(args.crisis.read_text(encoding="utf-8"))

    m_tr, m_va = train_test_split(
        misinfo, test_size=args.val_size, random_state=args.seed,
        stratify=[r["label"] for r in misinfo],
    )
    c_tr, c_va = train_test_split(
        crisis, test_size=args.val_size, random_state=args.seed,
        stratify=[r["humanitarian"] for r in crisis],
    )

    tokenizer = AutoTokenizer.from_pretrained(args.hf_model_id)

    misinfo_train = MisinfoDataset([r["claim"] for r in m_tr], [r["label"] for r in m_tr], tokenizer, args.max_len)
    misinfo_val = MisinfoDataset([r["claim"] for r in m_va], [r["label"] for r in m_va], tokenizer, args.max_len)
    crisis_train = CrisisDataset(
        [r["text"] for r in c_tr], [r["urgency"] for r in c_tr], [r["humanitarian"] for r in c_tr],
        tokenizer, args.max_len,
    )
    crisis_val = CrisisDataset(
        [r["text"] for r in c_va], [r["urgency"] for r in c_va], [r["humanitarian"] for r in c_va],
        tokenizer, args.max_len,
    )

    dl_kwargs = dict(batch_size=args.batch_size, num_workers=args.num_workers,
                     collate_fn=collate, pin_memory=device.type == "cuda")
    misinfo_loader = DataLoader(misinfo_train, shuffle=True, **dl_kwargs)
    crisis_loader = DataLoader(crisis_train, shuffle=True, **dl_kwargs)
    misinfo_val_loader = DataLoader(misinfo_val, shuffle=False, **dl_kwargs)
    crisis_val_loader = DataLoader(crisis_val, shuffle=False, **dl_kwargs)

    # ---- model ---------------------------------------------------------- #
    model = MultiTaskDeberta(args.hf_model_id, tasks=DEFAULT_TASKS)
    # deberta-v3-large ships fp16 weights; recent transformers loads them as-is.
    # AMP needs fp32 master weights (it casts to fp16 inside autocast), otherwise
    # GradScaler.unscale_ raises "Attempting to unscale FP16 gradients".
    model.float()
    if args.gradient_checkpointing:
        model.encoder.gradient_checkpointing_enable()
        model.encoder.config.use_cache = False
    if args.lora:
        from peft import LoraConfig, TaskType, get_peft_model

        lora_cfg = LoraConfig(
            task_type=TaskType.FEATURE_EXTRACTION,  # custom heads stay fully trainable
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            target_modules=["query_proj", "key_proj", "value_proj"],
            bias="none",
        )
        model.encoder = get_peft_model(model.encoder, lora_cfg)
        model.encoder.print_trainable_parameters()
    model.to(device)

    # ---- losses (class weights from TRAIN split) ------------------------ #
    losses: dict[str, nn.Module] = {
        "misinfo": nn.CrossEntropyLoss(),
        "urgency": FocalLoss(
            args.focal_gamma,
            class_weights([r["urgency"] for r in c_tr], model.tasks["urgency"].num_labels).to(device),
        ),
        "humanitarian": FocalLoss(
            args.focal_gamma,
            class_weights([r["humanitarian"] for r in c_tr], model.tasks["humanitarian"].num_labels).to(device),
        ),
    }

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    steps_per_epoch = len(misinfo_loader) + args.crisis_oversample * len(crisis_loader)
    total_steps = steps_per_epoch * args.epochs
    sched = get_linear_schedule_with_warmup(
        optim, int(total_steps * args.warmup_ratio), max(1, total_steps)
    )
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_metric = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    best_metrics: dict[str, dict[str, float]] = {}
    patience = 0

    for epoch in range(args.epochs):
        model.train()
        # One epoch = every misinfo batch once + every crisis batch `oversample`
        # times, drawn in a shuffled order. We only shuffle the ORDER of draws
        # (a list of tags) and pull one batch lazily per step -- tokenization
        # happens as batches are consumed, not all up front.
        order = ["misinfo"] * len(misinfo_loader) + ["crisis"] * (
            args.crisis_oversample * len(crisis_loader)
        )
        random.shuffle(order)
        mis_it = iter(misinfo_loader)
        cri_it = iter(crisis_loader)

        def next_batch(tag: str):
            nonlocal cri_it
            if tag == "misinfo":
                return ("misinfo",), next(mis_it)
            try:
                return CRISIS_TASKS, next(cri_it)
            except StopIteration:  # crisis is smaller; restart it for oversampling
                cri_it = iter(crisis_loader)
                return CRISIS_TASKS, next(cri_it)

        running = 0.0
        optim.zero_grad(set_to_none=True)
        pbar = tqdm(order, desc=f"epoch {epoch + 1}/{args.epochs}")
        for step, tag in enumerate(pbar, start=1):
            tasks_present, batch = next_batch(tag)
            with torch.amp.autocast(device.type, enabled=use_amp):
                loss = batch_loss(model, batch, tasks_present, losses, device)
            scaler.scale(loss).backward()
            scaler.unscale_(optim)
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            scaler.step(optim)
            scaler.update()
            optim.zero_grad(set_to_none=True)
            sched.step()
            running += float(loss.detach().item())
            pbar.set_postfix(loss=f"{running / step:.4f}")

        metrics = {
            "misinfo": evaluate_head(model, misinfo_val_loader, "misinfo", device),
            "urgency": evaluate_head(model, crisis_val_loader, "urgency", device),
            "humanitarian": evaluate_head(model, crisis_val_loader, "humanitarian", device),
        }
        mean_macro_f1 = float(np.mean([m["macro_f1"] for m in metrics.values()]))
        print(
            f"epoch {epoch + 1}: mean_macro_f1={mean_macro_f1:.4f} | "
            + " | ".join(f"{t}: acc={m['accuracy']:.3f} f1={m['macro_f1']:.3f}" for t, m in metrics.items())
        )

        if mean_macro_f1 > best_metric + args.min_delta:
            best_metric = mean_macro_f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_metrics = metrics
            patience = 0
        else:
            patience += 1
        if patience >= args.early_stopping_patience:
            print("early stopping")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    # Fold LoRA adapters into the encoder so the checkpoint reloads with the
    # standard loader (no peft needed at inference).
    if args.lora:
        model.encoder = model.encoder.merge_and_unload()

    save_multitask_checkpoint(model, tokenizer, args.output_dir, max_len=args.max_len)
    report = {
        "hf_model_id": args.hf_model_id,
        "best_mean_macro_f1": best_metric,
        "per_task": best_metrics,
        "n_train": {"misinfo": len(misinfo_train), "crisis": len(crisis_train)},
        "n_val": {"misinfo": len(misinfo_val), "crisis": len(crisis_val)},
        "lora": bool(args.lora),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nsaved model + metrics to {args.output_dir}")
    print(json.dumps(report["per_task"], indent=2))


if __name__ == "__main__":
    main()
