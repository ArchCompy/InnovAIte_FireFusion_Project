# FireFusion: ConvLSTM Training Run Log

Log of ConvLSTM bushfire-classifier training runs: configuration, data used, and outcomes. New runs are appended below as they're completed.

---

## Leading model

**Run 4: ConvLSTM-BiLSTM** has the best test-set PR-AUC logged (0.1335) and perfect precision (1.0000), the best-supported pick on the primary (threshold-independent) metric.

**Run 3**, a matched M1 baseline with BiLSTM turned off, is the most directly relevant comparison: it uses the same 2019 train / Jan-Mar 2020 val / Dec 10-31 2021 eval setup as Run 4, giving the closest controlled BiLSTM-vs-no-BiLSTM comparison in this log. Under this near-matched setup, BiLSTM wins on PR-AUC and precision, while the plain baseline has higher recall and F2 (0.1476 vs 0.1220).

| | PR-AUC | F2 | Precision | Recall |
| --- | --- | --- | --- | --- |
| **Run 4: BiLSTM** | **0.1335** | 0.1220 | 1.0000 | 0.1000 |
| Run 3: Matched M1 baseline | 0.1016 | **0.1476** | 0.2581 | 0.1333 |
| Run 1: Baseline | 0.0897 | 0.1373 | 0.4667 | 0.1167 |
| Run 5: M1 Baseline (attention comparison) | 0.1002 | 0.0617 | 1.0000 | 0.0500 |

---

## Field definitions

- **Split policy**: how train/val/test were divided. Either a ratio split or the date-based split.
- **Architecture**: `attention` mode and whether `use_bilstm` / `use_biconvlstm` were enabled. `"none"` + both `False` = the M1 baseline.
- **Total params**: model parameter count.
- **Best val loss**: lowest `MaskedTverskyLoss` or `MaskedFocalLoss` on validation, at the epoch whose weights were reloaded.
- **Threshold**: decision threshold selected on validation by maximizing F2, then applied unchanged to the test set.
- **PR-AUC**: precision-recall area under curve from test-set evaluation, the primary test-set comparison metric since it's threshold-independent (unlike Precision/Recall/F2, which depend on the selected decision threshold). Preferred over ROC-AUC here given how few positive cells are in these test sets.
- **Precision / Recall / F2 / ROC-AUC**: test-set metrics, computed only over valid (land) cells. ROC-AUC is noted as inflated by class imbalance in every run's own log output; compare PR-AUC first.

---

## Summary table

### Config

| Run | Data | Split policy | Architecture | Total params | Key hyperparams |
| --- | --- | --- | --- | --- | --- |
| 1: Baseline | 2021, restrictive satellite detections | Legacy 90% ratio (single year, 730 timesteps) | ConvLSTM, `attention="none"`, no BiLSTM/BiConvLSTM | 73,937 | `input_steps=30`, `hidden=(32,16)`, `dropout=0.2`, `lr=0.001`, `batch=8`, Tversky `α=0.3, β=0.7` |
| 2: Less restrictive detections | 2021, less restrictive satellite detections | Legacy 90% ratio (single year, 730 timesteps) | ConvLSTM, `attention="none"`, no BiLSTM/BiConvLSTM | 73,937 | `input_steps=15`, `hidden=(32,16)`, `dropout=0.2`, `lr=0.001`, `batch=8`, Tversky `α=0.3, β=0.7`, `epochs=60`, `patience=25` |
| 3: Matched M1 baseline (BiLSTM off) | Train 2019 / Val Jan-Mar 2020 / **Eval Dec 10-31 2021** | Date-based train/val (matches current script); eval on the same period as the other runs | ConvLSTM, `attention="none"`, `use_bilstm=False` (matches Run 4's config with BiLSTM off) | 73,937 (inferred; not printed in this log) | Same defaults as Run 4: `input_steps=30`, `hidden=(32,16)`, `dropout=0.2`, `lr=0.001`, `batch=8`, Tversky `α=0.3, β=0.7`, `epochs=50` (max), `patience=10` |
| 4: ConvLSTM-BiLSTM | Train 2019 / Val Jan-Mar 2020 / **Eval Dec 10–31 2021** | Date-based train/val (matches current script); eval on the same period as the other runs | ConvLSTM + BiLSTM, `use_bilstm=True` | not reported in log | Default hyperparameters: `input_steps=30`, `hidden=(32,16)`, `dropout=0.2`, `bilstm_hidden_size=8`, `lr=0.001`, `batch=8`, Tversky `α=0.3, β=0.7`, `epochs=50` (max) |
| 5: M1 Baseline (attention comparison) | 2021, restrictive detections, same dataset as Run 1 | Legacy 90% ratio, same split as Run 1 | ConvLSTM, `attention="none"` (M1) | 73,937 | `input_steps=30`, `hidden=(32,16)`, `lr=0.001`, `batch=1` (Run 1 used `batch=8`), Tversky `α=0.3, β=0.7`, `epochs=50`, `patience=10` |
| 6: M3 Patchwise Self-Attention | 2021, restrictive detections, same dataset as Run 1 & 5 | Legacy 90% ratio, same split as Run 1 & 5 | ConvLSTM + patchwise self-attention (layer 1), footprint 7×7, dilation 1, share_planes=8 | 110,369 | Same as Run 5 except architecture |
| 7: M2 Attention, 1 epoch smoke test | 2021, less restrictive detections, same labels as Run 2 | Legacy 90% ratio (single year, 730 timesteps) | ConvLSTM + patchwise attention | 110,369 | `input_steps=30`, `lr=0.001`, `epochs=1` (not early-stopped, hit configured max), `patience=10` |

### Outcome

| Run | Best val loss | Precision | Recall | Test F2 | Test PR-AUC | ROC-AUC | Threshold |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1: Baseline | 0.960823 (epoch 35) | 0.4667 | 0.1167 | 0.1373 | 0.0897 | 0.4946 | 0.6183 |
| 2: Less restrictive detections | 0.866349 (epoch 53) | 0.0607 | 0.0599 | 0.0601 | 0.0278 | 0.5826 | 0.0010 |
| 3: Matched M1 baseline (BiLSTM off) | 0.670757 (epoch 30) | 0.2581 | 0.1333 | 0.1476 | 0.1016 | 0.5995 | 0.8776 |
| 4: ConvLSTM-BiLSTM | 0.738823 (epoch 17) | 1.0000 | 0.1000 | 0.1220 | 0.1335 | 0.6491 | 0.8772 |
| 5: M1 Baseline (attention comparison) | 0.318840 (epoch 44) | 1.0000 | 0.0500 | 0.0617 | 0.1002 | 0.6916 | 0.0000 |
| 6: M3 Patchwise Self-Attention | 0.999788 (epoch 9, early-stopped) | 0.0000 | 0.0000 | 0.0000 | 0.0001 | 0.3708 | 0.3933 |
| 7: M2 Attention, 1 epoch smoke test | 0.998719 (epoch 1, only epoch) | 0.0007 | 0.3410 | 0.0034 | 0.0007 | 0.6352 | 0.5541 |

---

## Run details

### Run 1: Baseline (2021, restrictive satellite detections)

**Data**
- Grid: `(730, 142, 200, 7)`, a single year (~2021), 12-hourly timesteps
- Valid cells: 14,257 / 28,400 (50.2%)
- Labels: "restrictive" satellite detections, only 976 positive cells across the full grid (positive rate 0.0123%), pos_weight (neg/pos) ≈ 8150

**Split policy**
- 90% ratio split into train/val (657 timesteps), remaining 10% as test (73 timesteps)
- Train/val further split → train 558 / val 99 timesteps
- Windowed sequences: 528 train / 69 val / 43 test

**Architecture**
- `attention = "none"`, `use_bilstm = False`, `use_biconvlstm = False` (M1 baseline)
- `hidden_size_1 = 32`, `hidden_size_2 = 16`, `dropout = 0.2`
- Total params: 73,937

**Training config**
- Loss: Masked Tversky (`alpha=0.3`, `beta=0.7`)
- Optimizer: Adam, `lr = 0.001`
- `batch_size = 8`, `epochs = 50` (max), `patience = 10`
- `input_steps = 30`, `horizon = 1`

**Outcome**
- Early stopped at epoch 45; best val loss **0.960823** at epoch 35
- Selected threshold: **0.6183** (val F2 = 0.0811)

| Metric | Value |
| --- | --- |
| PR-AUC | 0.0897 |
| Skill (vs no-skill PR-AUC 0.0001) | 916.4x |
| Precision | 0.4667 |
| Recall | 0.1167 |
| F2 | 0.1373 |
| F1 | 0.1867 |
| IoU | 0.1029 |
| Brier | 0.0001 |
| ROC-AUC | 0.4946 (inflated by class imbalance) |
| TP / FP / FN / TN | 7 / 8 / 53 / 612,983 |
| Test positive rate | 0.0098% (60 of 613,051 cells) |

**Notes**
- Legacy 90% ratio split on a single year of data, not the current date-based policy; not directly comparable to runs using the newer split.

---

### Run 2: Less restrictive satellite detections (2021)

**Data**
- Grid: `(730, 142, 200, 7)`, same year/grid as Run 1
- Valid cells: 14,257 / 28,400 (50.2%), same as Run 1
- Labels: less restrictive satellite detections, 9,561 positive cells (vs. 976 in Run 1), positive rate 0.1202% (vs. 0.0123%), pos_weight (neg/pos) ≈ 831.1 (vs. ≈8150)

**Split policy** *(legacy, same as Run 1)*
- 90% ratio split into train/val (657 timesteps), remaining 10% as test (73 timesteps)
- Train/val further split → train 558 / val 99 timesteps
- Windowed sequences: 543 train / 84 val / 58 test (higher than Run 1 because `input_steps` dropped from 30 → 15)

**Architecture**
- `attention = "none"`, `use_bilstm = False`, `use_biconvlstm = False` (M1 baseline), same as Run 1
- `hidden_size_1 = 32`, `hidden_size_2 = 16`, `dropout = 0.2`, same as Run 1
- Total params: 73,937; same as Run 1

**Training config: differences from Run 1 flagged**
- Loss: Masked Tversky (`alpha=0.3`, `beta=0.7`), same as Run 1
- Optimizer: Adam, `lr = 0.001`; same as Run 1
- `batch_size = 8`, same as Run 1
- `input_steps = 15` (Run 1: 30, inferred from "Minimum needed: 16")
- `epochs = 60` (Run 1: 50)
- `patience = 25` (Run 1: 10)

**Outcome**
- Ran the full 60 epochs without early stopping; best val loss **0.866349** at epoch 53
- Selected threshold: **0.0010** (val F2 = 0.1463), notably low, model's positive scores are compressed near 0

| Metric | Value | vs. Run 1 |
| --- | --- | --- |
| PR-AUC | 0.0278 | ↓ (was 0.0897) |
| Skill (vs no-skill PR-AUC 0.0004) | 72.5x | ↓ (was 916.4x) |
| Precision | 0.0607 | ↓ (was 0.4667) |
| Recall | 0.0599 | ↓ (was 0.1167) |
| F2 | 0.0601 | ↓ (was 0.1373) |
| F1 | 0.0603 | ↓ (was 0.1867) |
| IoU | 0.0311 | ↓ (was 0.1029) |
| Brier | 0.0005 | ↑ (was 0.0001) |
| ROC-AUC | 0.5826 | ↑ (was 0.4946) |
| TP / FP / FN / TN | 19 / 294 / 298 / 826,295 | more of everything (more test windows + more positives) |
| Test positive rate | 0.0383% (317 of 826,906 cells) | ↑ (was 0.0098%) |

**Notes**
- Three hyperparameters changed alongside label restrictiveness (`input_steps`, `epochs`, `patience`), so the test-metric regression can't be attributed to label restrictiveness alone.

---

### Run 3: Matched M1 baseline (2019 data, BiLSTM off)

**Same configuration as Run 4 (ConvLSTM–BiLSTM), with `use_bilstm=False`.** This is the closest controlled BiLSTM-on/BiLSTM-off comparison logged so far, sharing the same 2019 train / Jan–Mar 2020 val / Dec 10–31 2021 eval setup as Run 4.

**Data**
- Training: 2019
- Validation: January–March 2020
- Evaluation: **December 10, 2021 12:00 – December 31, 2021 12:00 UTC** (same period as Run 4)
- Training labels: not reported in this log

**Architecture**
- `attention = "none"`, `use_bilstm = False`, `use_biconvlstm = False` (M1 baseline; Run 4 with BiLSTM turned off)
- `hidden_size_1 = 32`, `hidden_size_2 = 16`, `dropout = 0.2` (same defaults as Run 4)
- Total params: 73,937 (inferred from the matching M1 baseline architecture elsewhere in this log; not printed in this run's log)

**Training config**
- Loss: Tversky, `alpha = 0.3`, `beta = 0.7` (same defaults as Run 4)
- Optimizer: Adam, `lr = 0.001`
- `batch_size = 8`, `epochs = 50` (max), `patience = 10`
- `input_steps = 30`

**Outcome**
- Early stopped at epoch 40 (`Wait 10/10`); best val loss **0.670757** at epoch 30
- Selected threshold: **0.8776** (val F2 at threshold selection not reported in this log)

| Metric | Value |
| --- | --- |
| PR-AUC | 0.1016 |
| Skill (vs no-skill PR-AUC 0.0001) | 1038.4x |
| Precision | 0.2581 |
| Recall | 0.1333 |
| F2 | 0.1476 |
| F1 | 0.1758 |
| IoU | 0.0964 |
| Brier | 0.0001 |
| ROC-AUC | 0.5995 (inflated by class imbalance) |
| TP / FP / FN / TN | 8 / 23 / 52 / 612,968 |
| Test positive rate | 0.0098% (60 of 613,051 cells) |

**Notes**
- Under the same train/eval period as Run 4, this M1 baseline has higher recall and F2 than BiLSTM (0.1333/0.1476 vs. 0.1000/0.1220), but lower precision and PR-AUC (0.2581/0.1016 vs. 1.0000/0.1335); BiLSTM traded recall for precision here, not a clean win either way.

---

### Run 4: ConvLSTM–BiLSTM

Trained and validated on 2019–2020 data (2019 train, Jan–Mar 2020 val); evaluated on the same period as the other runs in this log.

**Data**
- Training: 2019
- Validation: January–March 2020
- Evaluation: **December 10, 2021 12:00 – December 31, 2021 12:00 UTC**
- Training labels: 7,227 positive cells / 10,214,233 negative cells, positive rate 0.0707%, pos_weight (neg/pos) ≈ 1413.3, a different (larger, "corrected") training-label source than Runs 1–2's 2021 legacy dataset

**Architecture**: confirmed default hyperparameters (not printed in this log, but per script/config defaults)
- ConvLSTM + BiLSTM (`use_bilstm = True`)
- `hidden_size_1 = 32`, `hidden_size_2 = 16`, `dropout = 0.2` (script defaults, same as Run 1)
- `bilstm_hidden_size = 8` (`ForecasterConfig` dataclass default, not overridden anywhere in the script)
- `input_steps = 30` (`INPUT_STEPS` default)

**Training config**
- Loss: Tversky, `alpha = 0.3`, `beta = 0.7` (hardcoded default in `main()`)
- Optimizer: Adam, `lr = 0.001`
- `batch_size = 8` (`BATCH_SIZE` default)
- `epochs = 50` (max), `patience = 10`

**Outcome**
- Early stopped at epoch 27; best val loss **0.738823** at epoch 17
- Selected threshold: **0.8772** (val F2 = 0.6514), notably higher/more confident than Runs 1–2's selected thresholds

| Metric | Value |
| --- | --- |
| PR-AUC | 0.1335 |
| Skill (vs no-skill PR-AUC 0.0001) | 1339.3x |
| Precision | 1.0000 |
| Recall | 0.1000 |
| F2 | 0.1220 |
| F1 | 0.1818 |
| IoU | 0.1000 |
| Brier | 0.00009128 |
| ROC-AUC | 0.6491 |
| TP / FP / FN / TN | 6 / 0 / 54 / 602,026 |
| Test positive rate | 0.0100% (60 of 602,086 cell-time targets) |
| Test set | 43 windows × 14,002 spatial cells (Dec 2021) |

**Notes**
- Precision 1.0000, Recall 0.1000: zero false positives but missed 54 of 60 fires, a far more conservative operating point than Runs 1–2. See Run 3 for the closest controlled comparison against the same architecture with BiLSTM off.

---

### Runs 5 & 6: M1 Baseline vs. M3 Patchwise Self-Attention

**Source:** "FireFusion: ConvLSTM Baseline (M1) vs. Patchwise Self-Attention (M3)" report, Emil Srambikudiyil Daniel

This is the cleanest architecture comparison logged so far: both runs used the **identical cached dataset, split, scaler, and loss function**; the only intentional variable is the attention mechanism. Both also use the same "restrictive satellite detections" 2021 dataset and legacy 90% ratio split as Run 1.

One variable was *not* held constant vs. Run 1 specifically: **`batch_size = 1`** here (reduced from the default 8 "due to GPU memory limits"), whereas Run 1 used `batch=8`. Runs 5 and 6 are directly comparable *to each other*; comparing Run 5 to Run 1 has this batch-size confound.

**Data & split** (identical for both runs, matches Run 1 exactly)
- Grid: `(730, 142, 200, 7)`; valid cells 14,257 / 28,400 (50.2%)
- Split: legacy 90% ratio → train+val 657 steps / test 73 steps, 85/15 within train+val
- Sequences: 528 train / 69 val / 43 test
- `input_steps = 30`, `horizon = 1`
- Training labels: 976 positive of 7,955,406 valid cell-timesteps (0.0123%), same dataset as Run 1
- Loss: Masked Tversky (`alpha=0.3`, `beta=0.7`); Optimizer: Adam, `lr=0.001`
- `epochs = 50` (max), `patience = 10`
- **`batch_size = 1`** (not 8, see caveat above)

**Architecture**

|  | Run 5: M1 Baseline | Run 6: M3 Self-Attention |
| --- | --- | --- |
| Gate operator | Standard Conv2d | Patchwise self-attention (layer 1) |
| Attention footprint / dilation | n/a | 7×7, dilation 1 |
| Share planes | n/a | 8 |
| Hidden sizes (layer 1 / 2) | 32 / 16 | 32 / 16 |
| Total parameters | 73,937 | 110,369 |
| Dropout | not reported in this source | not reported in this source |

**Training behaviour**

|  | Run 5: M1 Baseline | Run 6: M3 Self-Attention |
| --- | --- | --- |
| Epochs run | 50 (completed) | 19 (early-stopped, patience 10) |
| Best epoch / best val loss | 44 / 0.318840 | 9 / 0.999788 |
| Selected threshold (val F2) | 0.0000 (F2 = 0.0362) | 0.3933 (F2 = 0.0084) |

Both models spent their first ~19 epochs pinned near val loss 0.999: the Tversky loss's "predict nothing" trivial solution under this class imbalance. The baseline got enough small improvements during that stretch to keep its patience counter alive until it broke out around epoch 20–24, converging to 0.3188 by epoch 27. The self-attention run's last improvement was epoch 9; with no improvement in the next 10, it was early-stopped at epoch 19, **before** reaching the point in training where the baseline broke through the same plateau.

**Test set performance**

| Metric | Run 5: M1 Baseline | Run 6: M3 Self-Attention |
| --- | --- | --- |
| PR-AUC (primary metric, threshold-independent) | 0.1002 | 0.0001 (= no-skill floor) |
| Skill vs. no-skill (0.0001) | 1024x | 0.7x |
| Precision | 1.0000 | 0.0000 |
| Recall | 0.0500 | 0.0000 |
| F1 | 0.0952 | 0.0000 |
| F2 | 0.0617 | 0.0000 |
| IoU | 0.0500 | 0.0000 |
| ROC-AUC (inflated by imbalance) | 0.6916 | 0.3708 |
| Brier | 0.0001 | 0.0011 |
| TP / FN | 3 / 57 | 0 / 60 |
| FP | 0 | 0 |

Out of 60 fire cells in the test set, M1 correctly flagged 3 with zero false positives; M3 flagged none and scored exactly at the no-skill PR-AUC floor.

**Notes**
- Not conclusive evidence against attention: M3's early stopping likely triggered right before the plateau breakthrough that M1 needed the same number of extra epochs to reach.

---

### Run 7: M2 Attention, less restrictive detections, 1 epoch smoke test

**Device:** CUDA

**Not a meaningful training result: logged for completeness/traceability, not for comparison.** `Epochs: 1` was the configured max (not an early stop), so the model trained for a single gradient pass over all batches. Its test metrics (128,628 false positives against 89 true positives; Brier 0.2765 vs. ~0.0001–0.001 for fully-trained runs) are consistent with a near-initialization model, not a converged one. Treat this as a smoke test / pipeline sanity check.

**Data**
- Grid: `(730, 142, 200, 7)`; valid cells 14,257 / 28,400 (50.2%), same as all prior runs
- Labels: less restrictive satellite detections, 9,561 positive cells, positive rate 0.1202%, pos_weight ≈ 831.1, **same label source as Run 2**, but not a clean comparison to it (see below)
- Split: legacy 90% ratio → train+val 657 steps / test 73 steps (same as Runs 1–2, 5–6)
- `input_steps = 30` (`Minimum needed: 31`), **differs from Run 2's `input_steps = 15`**, despite sharing the same label source
- Sequences: 528 train / 69 val / 43 test

**Architecture**
- ConvLSTM + patchwise attention (`ATTENTION='patchwise'`), 110,369 total parameters; matches Run 6's M3 architecture exactly (same param count), so presumably the same `footprint=7`, `dilation=1`, `share_planes=8`, `hidden=(32,16)` configuration, though not restated in this log

**Training config**
- Loss: Tversky (`alpha`/`beta` not printed in this log; not confirmed as default here)
- Optimizer: Adam, `lr = 0.001`
- `epochs = 1`, `patience = 10` (irrelevant at 1 epoch)

**Outcome**
- Single epoch: train loss 0.995000, val loss 0.998719, right at the "predict nothing" trivial-solution plateau every other run in this log spent its first ~9–24 epochs stuck in
- Selected threshold: 0.5541 (val F2 = 0.0021, near zero)

| Metric | Value |
| --- | --- |
| PR-AUC | 0.0007 |
| Skill (vs no-skill PR-AUC 0.0004) | 1.6x |
| Precision | 0.0007 |
| Recall | 0.3410 |
| F2 | 0.0034 |
| F1 | 0.0014 |
| IoU | 0.0007 |
| Brier | 0.2765 (very poor, see caveat) |
| ROC-AUC | 0.6352 |
| TP / FP / FN / TN | 89 / 128,628 / 172 / 484,162 |
| Test positive rate | 0.0426% (261 of 613,051 cells) |

**Notes**
- High recall (0.3410) is an artifact of broad over-prediction (128,628 false positives), not genuine skill; not a meaningful result given only 1 epoch was trained.

---
 
# Analysis and recommendations
 
The runs above establish a working pipeline and a consistent evaluation protocol across seven configurations. The section below reviews those runs for the patterns that look worth pursuing, the areas where the current setup limits what the results can show, and a suggested order of work from here. The current ranking is best treated as provisional rather than settled, and the recommendations below are ordered partly by how much they would tighten that signal.
 
---
 
## 1. Directions that look promising
 
### Batch size and optimizer step count
 
The largest effect visible anywhere in this log came from Runs 1 and 5, which share the same cached dataset, split, scaler, architecture, loss function, learning rate and `input_steps`. The one difference is `batch_size` 8 against 1, reduced in Run 5 to fit GPU memory. Best validation loss moved from 0.960823 to 0.318840.
 
That gap is larger than anything produced by the architecture changes tested so far. Run 1's best validation loss of 0.960823 sits close to the trivial "predict nothing" solution that the Run 5/6 section identifies, while Run 5 moved well clear of it. This indicates the models tested so far may have been limited more by optimisation than by capacity.
 
A deliberate sweep at batch 1, 2, 4 and 8 with everything else fixed could be worth doing. It is also worth separating the two mechanisms in play, since batch 1 delivers both noisier gradients and eight times the optimizer steps per epoch. If step count is the driver, raising the learning rate or the epoch budget at batch 8 should reproduce the benefit at lower wall-clock cost.
 
### Early stopping patience
 
Every run in this log spends its first 9 to 24 epochs near validation loss 0.999, which the Run 5/6 section correctly identifies as the Tversky trivial solution under this class imbalance. With `patience = 10`, the stopping window is shorter than the plateau itself, so runs can be halted before learning has begun. Run 6 stopped at epoch 19; Run 5 cleared the same plateau on the same data at roughly epoch 20 to 24.
 
Raising patience to 25 to 30, or adding a minimum-epoch floor that blocks early stopping before around epoch 30, would remove this as a source of variation between runs. This is a low-cost change with a high chance of altering conclusions.
 
### The date-based split and multi-year training
 
Runs 3 and 4 reached validation losses of 0.670757 and 0.738823, against 0.960823 for Run 1 on the legacy ratio split. Both the split policy and the corrected label source differ, so the effect is not cleanly attributable, but both point the same way.
 
Extending training beyond a single year is the natural next step. It increases the volume of fire events the model sees, which is the binding constraint at a 0.0123% positive rate, and it lets the training set span more than one fire regime.
 
### BiLSTM
 
Run 4 shifted the operating point toward precision relative to the matched baseline in Run 3. The log's note is the key reading: this trades recall for precision rather than dominating on both. For a warning application recall usually carries more weight, which is why F2 is the selected operating metric, and Run 3 leads on F2. BiLSTM is worth carrying forward as a candidate rather than being adopted as the settled architecture.
 
---
 
## 2. Potential areas to strengthen
 
### Satellite detection restrictiveness
 
The restrictive detections should remain the default for now. The loose-detection runs point the other way, but neither is yet in a position to settle the question. Run 2 varied `input_steps`, `epochs` and `patience` alongside the label source, which its own notes flag, and Run 7 is a single-epoch smoke test.
 
What does support keeping the restrictive set is the Run 2 result. The selected threshold fell to 0.0010 and precision to 0.0607, against 0.4667 in Run 1, which describes a model spreading low confidence across a wide area rather than committing anywhere. Validation loss also improved under the loose labels, 0.866349 against 0.960823, while test precision fell. An objective that becomes easier to fit while predictions become worse is consistent with the model absorbing label noise. The additional 8,585 positive cells are by construction the detections the restrictive filter judged least reliable.
 
The counterweight is that 976 positive cells across a full year is very little signal for a 73,937-parameter model, so the loose set is not without value. A controlled run with Run 1's exact hyperparameters would resolve it. If that does not fit the remaining schedule, a middle option is likely to be more informative than either extreme, either retaining the extra detections at a reduced loss weight, or admitting only those above a stated confidence level. Until such a run exists, the position to state is that restrictive detections are the working default and the controlled comparison remains outstanding.
 
### Attention architectures
 
Run 6 is better read as a result about the stopping criterion than about attention. Its own note makes this point, and it deserves more weight than its current placement suggests: M3 stopped at epoch 19, before reaching the plateau breakthrough that M1 needed a comparable number of extra epochs to reach on identical data.
 
Attention therefore remains untested rather than ruled out. Rerunning M3 with patience 30 and batch 1 would give the first genuine read on it. Given that M3 adds 36,432 parameters over the baseline, it is a reasonable candidate to benefit most from the optimisation changes described above.
 
### Evaluation window and confidence intervals
 
The December 10 to 31, 2021 window is a demanding basis for ranking. Sixty positive cells across three weeks is a small sample, and every comparison in this log resolves to whether a model caught 3, 6 or 8 of them.
 
Two additions would strengthen this considerably. First, evaluating across several separate windows, or across a longer span, would widen the positive base. Second, bootstrapped confidence intervals over the test positives would let the report state directly whether an observed difference is distinguishable from sampling noise. Demonstrating that several configurations are statistically indistinguishable is a more defensible finding than naming a winner that the sample cannot support.
 
This relates to another point involving threshold transfer. Runs 3 and 4 validate on January to March 2020 and test on December 2021, which are very different fire regimes. Run 4's validation F2 of 0.6514 falls to 0.1220 on test. Much of that gap reflects regime shift, which means the decision threshold is being chosen under conditions unlike those it is applied in. Selecting the threshold on a validation period closer to the test regime, or treating threshold-independent metrics as primary and the operating point as a separate downstream step, would make the reported figures more stable.
 
### Scoring tolerance
 
At 142 × 200 cells on 12-hourly steps, a prediction one cell away or one timestep early registers as a false positive and a false negative at once. This is the strictest available scoring rule, and it accounts for part of why recall across the log sits between 0 and 0.1333.
 
Reporting neighbourhood-tolerant scores alongside the exact figures would show whether the models hold coarse spatial skill that exact matching currently conceals. A common convention counts a hit where a positive prediction falls within 1 to 2 cells and plus or minus one timestep of a true detection. Both sets of figures should be reported rather than one replacing the other, since the exact scores remain the conservative benchmark.
 
### Naive baselines
 
The skill ratios above are measured against a random no-skill classifier. That is a permissive reference point, and it makes figures such as 916x and 1339x read as stronger than the underlying performance warrants.
 
Two baselines would anchor the comparison properly:
 
- **Persistence**, where cells detected at time *t* are predicted positive at *t+1*. Fires tend to persist and cluster together, so this is likely to be competitive with the current models.
- **Climatology or a rule baseline**, using per-cell historical fire frequency, or a threshold rule on the weather channels already present in the grid.
These are inexpensive to compute on the existing test set and they set the bar that any architecture work has to clear. Establishing them early determines how much of the remaining effort should go into architecture at all.
 
---
 
## 3. Suggested priority order
 
| | Action | Rationale |
| --- | --- | --- |
| 1 | Add persistence and climatology baselines on the existing test set | Sets the reference point that all architecture comparisons depend on; low cost |
| 2 | Add bootstrap confidence intervals over the test positives | Establishes whether current differences are distinguishable from noise |
| 3 | Raise patience to 25–30 and add a minimum-epoch floor | Removes the plateau-length confound affecting Run 6 and possibly others |
| 4 | Sweep batch size (1 / 2 / 4 / 8) at fixed seed and architecture | Tests the largest observed effect in the log under controlled conditions |
| 5 | Run the controlled restrictive-versus-loose label comparison | Settles the label question that Runs 2 and 7 could not isolate |
| 6 | Rerun M3 attention under the revised stopping criterion | Gives attention its first uncompromised test |
| 7 | Add neighbourhood-tolerant scoring alongside exact matching | Reveals coarse spatial skill that strict matching may be hiding |
| 8 | Record seeds and repeat the two leading configurations three times | Quantifies run-to-run variance before any final architecture claim |
 
Items 1 to 3 are the highest value relative to cost, and all three are achievable without retraining any model from scratch.