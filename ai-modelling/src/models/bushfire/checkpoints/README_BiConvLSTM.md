# ConvLSTM–BiConvLSTM Trained Model

## Model files

- `convlstm_biconvlstm_forecaster.pth`: trained weights and architecture configuration.
- `convlstm_biconvlstm_scaler.pkl`: fitted weather scaler, input metadata and validation-selected threshold.

Use these files together. The existing ConvLSTM baseline files and the ConvLSTM–BiLSTM files remain unchanged.

## Configuration

The model combines ConvLSTM with a BiConvLSTM layer, with BiConvLSTM hidden size 8 per direction, kernel size 3, and 87,825 trainable parameters. Attention and the per-cell BiLSTM are disabled, so the experiment measures only the assigned architecture.

Inputs consist of seven scaled weather features followed by historical `is_burning`, which is not scaled. Each prediction uses 30 consecutive 12-hour observations to forecast the next interval.

Training settings: seed 42, batch size 8, learning rate 0.001, maximum 50 epochs, early-stopping patience 10, Adam optimiser, and Tversky loss with α=0.3 and β=0.7.

Training stopped at epoch 22 by early stopping. The best validation model was selected at epoch 12, with validation loss 0.999508.

Starting commit: `ebae869f30ffd4732f929dd9ae3c444ee28a7128`. Branch: `feat/train-biconvlstm-benchmark`. Trained on a Tesla T4 in 1.25 hours, with gradient checkpointing enabled so that batch size 8 fitted in memory (see *Memory note* below).

## Data partitions

The experiment used the 2021 dataset: 730 twelve-hourly timesteps from 1 January to 31 December 2021, on a 142 × 200 grid with 14,257 spatial cells that have weather data. Partitions follow the agreed chronological split of 76.5% / 13.5% / 10%.

| Partition | Target dates (UTC) | Windows | Positive targets |
|---|---|---:|---:|
| Training | 16 January 00:00 – 6 October 12:00 | 528 | 991 |
| Validation | 7 October 00:00 – 25 November 00:00 | 69 | 34 |
| Test | 25 November 12:00 – 31 December 12:00 | 43 | 60 |

The first 15 days of 2021 provide input history. Each target uses the preceding 30 observations, including history from the previous partition where needed.

The scaler was fitted on the training partition only. Model selection and threshold selection used the validation partition only. The saved threshold is **0.1982**, chosen by validation F2, which reached only 0.0007.

The positive rate in training is 0.0125%, giving a negative-to-positive ratio of approximately 8,027:1.

## Evaluation results

Evaluated on the test partition with the saved scaler and the validation-selected threshold. The persistence baseline predicts that a cell is burning in the next interval if it was burning in the current one; it requires no training and is included as a reference point.

| Metric | ConvLSTM–BiConvLSTM | Persistence baseline |
|---|---:|---:|
| Prediction windows | 43 | 43 |
| Positive targets | 60 | 60 |
| True positives | 0 | 8 |
| False positives | 3,130 | 42 |
| False negatives | 60 | 52 |
| Precision | 0.00% | 16.00% |
| Recall | 0.00% | 13.33% |
| F1 | 0.0000 | 0.1455 |
| F2 | 0.0000 | 0.1379 |
| PR-AUC | 0.0001 | 0.0214 |

Additional threshold-independent measures for the trained model: ROC-AUC 0.4078 and Brier score 0.0008. The no-skill PR-AUC reference for this split is 0.0001, so the model's PR-AUC of 0.0001 corresponds to 0.8× the no-skill reference — that is, at or slightly below chance.

Positive targets represent grid-cell/time observations, not distinct bushfire events.

## Training behaviour

Tversky loss remained between 0.9977 and 0.9995 for every epoch, which indicates essentially no overlap between predicted and actual fire cells at any point in training. Training loss drifted downward slightly while validation loss fluctuated without a trend, and the best validation loss (epoch 12) improved on the first epoch by less than 0.0004.

## Data preparation notes

Three issues were found while preparing the grids from `forecaster_test_data.csv` and `satellite_detections_within_fires.csv`. They affect anyone rebuilding caches from these sources.

1. **Duplicate timestamps.** The environmental CSV writes midnight in two different string formats. Collecting unique timestamp strings before parsing produces 1,095 half-filled slots instead of 730 twelve-hourly steps. Datetimes must be parsed before deduplication; the duplicate slots were merged for this experiment.
2. **Fire row alignment.** Satellite detections require the `cell_y − 1` correction. Without it, 30 detections fall outside the weather mask; with it, 15 do, and the validation and test target counts (34 and 60) match the reference counts reported for the ConvLSTM–BiLSTM experiment.
3. **Missing land variables.** Approximately 1.8% of values for the three ERA5-Land features (`temperature_2m`, `skin_temperature`, `surface_solar_radiation_downwards`) are missing, on a fixed set of about 255 coastal cells at every timestep, since ERA5-Land has no values over water. The pipeline imputes these as the feature mean after scaling. The three plain ERA5 features have no missing values.

## Limitations and conclusions

The model detected none of the 60 positive targets in the test partition and produced 3,130 false positives, with a PR-AUC at the no-skill reference. On this split the trained model performs no better than chance and is outperformed by the persistence baseline on every metric reported above.

The same 2021 configuration is documented as unstable and non-detecting for the ConvLSTM–BiLSTM architecture, including across the seed variations tested there. Two different architectures failing in the same way on the same split suggests that the limitation lies in the data setup for this split rather than in the recurrent layer chosen. Contributing factors include extreme class imbalance (0.0125% positive), a validation partition containing only 34 positive targets — too few for reliable threshold selection — and a test partition drawn from a seasonally distinct period at the end of the year.

A controlled architecture comparison remains outstanding. The ConvLSTM–BiLSTM results reported elsewhere use a different data split (train 2019, validate January–March 2020, test April–December 2020), a different spatial mask of 14,002 cells, and corrected fire labels, so those figures are not directly comparable with the results above. A like-for-like comparison requires both architectures to be trained on identical data, labels and mask, either by running both on the 2021 split used here or by running both on the 2019–2020 split, which needs the shared grid caches for those years.

These results do not support using this configuration as a standalone bushfire detection system. They are recorded as a valid negative result for the benchmark: on the 2021 split, the BiConvLSTM configuration does not improve on the baseline.

## Reproducing this run

No modified training script is committed. The run used a copy of
`src/training/ts_convlstm_forecaster_train.py` at the commit above, with the
changes listed below and nothing else. Applying them reproduces the run
exactly.

**1. Architecture.** In the `ForecasterConfig(...)` call, add:

```python
use_bilstm=False,
use_biconvlstm=True,
biconvlstm_hidden_size=8,
biconvlstm_kernel_size=3,
```

**2. Random seed.** At the start of `main()`, before the model is built:

```python
np.random.seed(42)
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
```

**3. Output filenames.** Point `MODEL_SAVE_PATH` and `SCALER_SAVE_PATH` at
`convlstm_biconvlstm_forecaster.pth` and `convlstm_biconvlstm_scaler.pkl` so
the baseline files are not overwritten.

**4. Cache paths.** Point `GRID_CACHE_PATH` and `LABEL_CACHE` at the prepared
2021 grids, built as described under *Data preparation notes* above.

**5. Checkpoint safety (optional).** Saving the model whenever validation
improves, rather than only at the end, protects long runs against session
loss. It does not affect results.

Every other setting — batch size, learning rate, epochs, patience, loss,
optimiser, split ratios and threshold selection — is used unchanged from the
committed script.

### Memory note

Batch size 8 does not fit in 16 GB of GPU memory with this architecture
unless gradient checkpointing is enabled for the ConvLSTM and BiConvLSTM
cells. The repository enables checkpointing only for attention cells; the
condition was relaxed locally for this run and the BiConvLSTM layer was
wrapped the same way. Peak memory then fell to 5.5 GB. Checkpointing
recomputes activations during the backward pass, so results are unchanged
and only training time increases. This change is not committed here and can
be raised separately if the team wants the benchmark to run on 16 GB GPUs.

### Run artefacts

The training log, per-epoch loss history and an `evidence.json` recording
the configuration, dependency versions, GPU and timings were kept with the
run and are available on request.

